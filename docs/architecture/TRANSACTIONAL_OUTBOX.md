# Transactional Outbox Pattern Implementation

## Overview

VisionScope implements the **Transactional Outbox pattern** to solve the dual-write problem and ensure reliable event publishing in distributed systems. This enterprise pattern guarantees that domain events are never lost, even in the face of system failures, by persisting events in the same transaction as business data.

## The Dual-Write Problem

Without the Transactional Outbox pattern, systems face the dual-write problem:

1. **Business Transaction** - Update database records (e.g., deduct credits)
2. **Event Publishing** - Send event to message bus (e.g., `CreditDeductedEvent`)

If the message bus is unavailable after the database transaction commits, the event is lost forever, leading to:

- **Data inconsistency** - Credits deducted but analytics not updated
- **Missing notifications** - Users not informed of credit changes
- **Billing discrepancies** - Revenue tracking out of sync

## Solution: Transactional Outbox

The outbox pattern solves this by:

1. **Single Transaction** - Store business data AND events in same database transaction
2. **Background Publisher** - Separate process publishes events from outbox to message bus
3. **Retry Logic** - Failed events are automatically retried with exponential backoff
4. **Idempotency** - Events marked as published to prevent duplicates

## Architecture Components

### 1. Database Model (`models/event_outbox.py`)

```python
class EventOutbox(Base):
    """Stores domain events for reliable publishing"""
    __tablename__ = "event_outbox"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(UTC), nullable=False)
    correlation_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Indexes for performance
    __table_args__ = (
        Index("idx_event_outbox_published", "published"),
        Index("idx_event_outbox_created_at", "created_at"),
    )
```

### 2. CQRS Operations (`building_blocks/messaging/outbox_cqrs.py`)

#### Commands

```python
@dataclass
class SaveEventToOutboxCommand(ICommand):
    """Save a domain event to the outbox table"""
    event: IEvent

    def __post_init__(self) -> None:
        if not isinstance(self.event, IEvent):
            raise ValueError("event must implement IEvent interface")

@dataclass
class MarkEventAsPublishedCommand(ICommand):
    """Mark an outbox event as successfully published"""
    event_id: UUID

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id is required")
```

#### Queries

```python
@dataclass
class GetUnpublishedEventsQuery(IQuery[list[EventOutbox]]):
    """Get events from outbox that haven't been published yet"""
    limit: int = 100

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("limit must be positive")
```

#### Handlers

```python
class SaveEventToOutboxHandler(ICommandHandler[SaveEventToOutboxCommand]):
    """Saves domain events to outbox table for reliable publishing"""

    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def handle(self, command: SaveEventToOutboxCommand) -> None:
        outbox_event = EventOutbox.from_event(command.event)
        self.db_session.add(outbox_event)
        await self.db_session.flush()
```

### 3. Pipeline Behavior (`building_blocks/behaviors/pipeline_behaviors.py`)

The `OutboxBehavior` automatically saves domain events during command processing:

```python
class OutboxBehavior(IPipelineBehavior[TRequest, TResponse]):
    """Pipeline behavior that saves domain events to outbox during command processing"""

    def __init__(self, mediator: IMediator) -> None:
        self.mediator = mediator

    async def handle(
        self,
        request: TRequest,
        next_handler: RequestHandlerDelegate[TResponse]
    ) -> TResponse:
        # Execute the actual command/query handler
        response = await next_handler(request)

        # Check if this request has domain events to persist
        if hasattr(request, 'events') and request.events:
            for event in request.events:
                save_command = SaveEventToOutboxCommand(event=event)
                await self.mediator.send(save_command)

        return response
```

### 4. Background Publisher (`building_blocks/messaging/outbox_publisher.py`)

The background publisher retrieves unpublished events and publishes them to the message bus:

```python
class OutboxEventPublisher:
    """Background service that publishes events from outbox to message bus"""

    def __init__(self, db_session: AsyncSession, message_bus: IMessageBus, mediator: IMediator) -> None:
        self.db_session = db_session
        self.message_bus = message_bus
        self.mediator = mediator
        self.event_type_registry: dict[str, type[IEvent]] = {}
        self.is_running = False
        self.poll_interval = 5.0  # seconds
        self.batch_size = 100

    def register_event_type(self, event_type: str, event_class: type[IEvent]) -> None:
        """Register an event type for deserialization"""
        self.event_type_registry[event_type] = event_class

    async def start_publishing(self) -> None:
        """Start the background publishing loop"""
        self.is_running = True
        while self.is_running:
            try:
                await self.process_unpublished_events()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in outbox publisher: {e}")
                await asyncio.sleep(self.poll_interval * 2)  # Back off on error

    async def process_unpublished_events(self) -> None:
        """Process a batch of unpublished events"""
        query = GetUnpublishedEventsQuery(limit=self.batch_size)
        unpublished_events = await self.mediator.send(query)

        for outbox_event in unpublished_events:
            try:
                # Reconstruct the original event
                event = outbox_event.reconstruct_event()

                # Publish to message bus
                await self.message_bus.publish(event)

                # Mark as published
                mark_command = MarkEventAsPublishedCommand(event_id=outbox_event.id)
                await self.mediator.send(mark_command)

                await self.db_session.commit()

            except Exception as e:
                logger.error(f"Failed to publish event {outbox_event.id}: {e}")
                await self.db_session.rollback()
                # Event remains unpublished and will be retried
```

## Database Migration

The outbox table is created with an Alembic migration:

```python
# data/alembic/versions/002_event_outbox.py
"""Add event outbox table for transactional outbox pattern

Revision ID: 002
Revises: 001
Create Date: 2025-10-08 10:00:00.000000
"""

def upgrade() -> None:
    # Create event_outbox table
    op.create_table(
        'event_outbox',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=255), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('published', sa.Boolean(), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('correlation_id', sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index('idx_event_outbox_published', 'event_outbox', ['published'])
    op.create_index('idx_event_outbox_created_at', 'event_outbox', ['created_at'])
```

## Usage Examples

### 1. Command Handler with Domain Events

```python
@dataclass
class DeductCreditsCommand(ICommand):
    workspace_id: UUID
    amount: int
    operation_type: str
    events: list[IEvent] = field(default_factory=list)  # Domain events

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Amount must be positive")

class DeductCreditsHandler(ICommandHandler[DeductCreditsCommand]):
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    async def handle(self, command: DeductCreditsCommand) -> None:
        # Business logic - deduct credits
        workspace = await self.get_workspace(command.workspace_id)
        workspace.deduct_credits(command.amount)

        # Raise domain event
        event = CreditDeductedEvent(
            workspace_id=command.workspace_id,
            amount=command.amount,
            remaining_credits=workspace.credits,
            operation_type=command.operation_type
        )
        command.events.append(event)  # OutboxBehavior will persist this

        # Save workspace changes
        await self.db_session.flush()
```

### 2. Setup and Registration

```python
# Initialize mediator with outbox behavior
mediator = EnterpriseMediator()
mediator.add_pipeline_behavior(OutboxBehavior(mediator))

# Register handlers
mediator.register_command_handler(DeductCreditsCommand, DeductCreditsHandler(db_session))
mediator.register_command_handler(SaveEventToOutboxCommand, SaveEventToOutboxHandler(db_session))

# Start background publisher
publisher = OutboxEventPublisher(db_session, message_bus, mediator)
publisher.register_event_type("CreditDeductedEvent", CreditDeductedEvent)
await publisher.start_publishing()
```

## Enterprise Benefits

### Reliability

- **Zero Event Loss** - Events persisted transactionally with business data
- **Automatic Retry** - Failed events automatically retried by background publisher
- **Failure Recovery** - System can recover from message bus outages

### Consistency

- **ACID Guarantees** - Events and business data updated atomically
- **Event Ordering** - Events processed in creation order
- **Exactly-Once Delivery** - Events marked as published to prevent duplicates

### Observability

- **Event History** - Complete audit trail of all events in database
- **Publishing Status** - Visibility into which events have been published
- **Error Tracking** - Failed events remain in outbox for debugging

### Performance

- **Batching** - Events published in configurable batches
- **Indexing** - Optimized queries for unpublished events
- **Async Processing** - Non-blocking event publication

### Scalability

- **Horizontal Scaling** - Multiple publisher instances can process different event types
- **Load Distribution** - Events can be partitioned by correlation ID or workspace
- **Backpressure Handling** - Publisher can throttle based on message bus capacity

## Monitoring and Alerts

### Key Metrics

- **Unpublished Event Count** - Monitor outbox table size
- **Publishing Latency** - Time between event creation and publication
- **Error Rate** - Percentage of failed publication attempts
- **Throughput** - Events published per second

### Recommended Alerts

- Alert if unpublished events > 1000 (potential message bus issue)
- Alert if publishing latency > 60 seconds (performance degradation)
- Alert if error rate > 5% (system health issue)

## Testing

### Unit Tests

```python
async def test_outbox_behavior_saves_events():
    # Arrange
    mediator = create_test_mediator()
    command = DeductCreditsCommand(workspace_id=UUID(), amount=100, operation_type="analysis")
    event = CreditDeductedEvent(workspace_id=command.workspace_id, amount=100, remaining_credits=900)
    command.events.append(event)

    # Act
    await mediator.send(command)

    # Assert
    outbox_events = await mediator.send(GetUnpublishedEventsQuery())
    assert len(outbox_events) == 1
    assert outbox_events[0].event_type == "CreditDeductedEvent"
```

### Integration Tests

```python
async def test_end_to_end_event_publishing():
    # Test that events flow from command -> outbox -> message bus
    publisher = OutboxEventPublisher(db_session, mock_message_bus, mediator)
    publisher.register_event_type("CreditDeductedEvent", CreditDeductedEvent)

    # Execute command that raises event
    await mediator.send(DeductCreditsCommand(workspace_id=UUID(), amount=100))

    # Process outbox
    await publisher.process_unpublished_events()

    # Verify event was published
    mock_message_bus.publish.assert_called_once()
```

## Migration from Direct Publishing

To migrate existing code from direct event publishing to the transactional outbox:

1. **Add OutboxBehavior** to your mediator pipeline
2. **Update command handlers** to append events to `command.events` instead of direct publishing
3. **Start background publisher** with registered event types
4. **Monitor** unpublished event count during rollout

The migration can be done gradually - the outbox pattern works alongside existing direct publishing until fully migrated.
