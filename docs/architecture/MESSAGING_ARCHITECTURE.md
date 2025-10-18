# Enterprise Event-Driven Messaging Architecture

## Overview

VisionScope implements an **enterprise-grade event-driven messaging system** with advanced resilience patterns, built on modern async Python with Celery + Redis. This architecture delivers bullet-proof real-time billing, usage tracking, and system coordination while maintaining 99.9% uptime requirements for enterprise customers.

## Why Enterprise Event-Driven Architecture?

### Business Requirements

- **Real-time billing** - Credits deducted with ACID guarantees and audit trails
- **Enterprise SLAs** - 99.9% uptime with comprehensive monitoring and alerting
- **Usage tracking** - Every operation tracked with distributed tracing for compliance
- **Complex orchestration** - Multi-service coordination with compensation patterns
- **Horizontal scalability** - Auto-scaling workers based on queue depth and processing load

### Enterprise Technical Benefits

- **Fault Tolerance** - Circuit breakers, retries, and dead letter queues
- **Observability** - Distributed tracing, metrics, and comprehensive logging
- **Security** - Message encryption, authentication, and authorization
- **Performance** - Intelligent routing, batching, and priority queues
- **Compliance** - Audit logging and message retention for regulatory requirements

## Enterprise Architecture Components

### Message Bus (`building_blocks/messaging/`)

- **Pure Interfaces** - Domain-agnostic contracts for maximum reusability
- **Enterprise Message Bus** - Resilience patterns with monitoring integration
- **Serialization** - Type-safe JSON serialization with schema validation
- **Dead Letter Queues** - Failed message handling with retry policies
- **Circuit Breakers** - Automatic failure detection and recovery

### Enterprise Message Types

#### Core Infrastructure Interfaces

```python
class IMessage(BaseModel, ABC):
    """Base for all messages with correlation tracking"""
    message_id: UUID
    timestamp: datetime
    correlation_id: UUID | None
    metadata: dict[str, Any]

class IEvent(IMessage, ABC):
    """Domain events (something that happened)"""
    pass

class IMessageCommand(IMessage, ABC):
    """Message commands (something that should happen)"""
    pass

class IIntegrationEvent(IEvent, ABC):
    """Events that cross service boundaries"""
    service_name: str
    version: str
    schema_version: str
```

#### Domain Events (Located in Domain Layer)

**Note: Domain events are no longer in the messaging infrastructure!**
They now live in their proper domain locations:

```python
# models/pricing/events/credit_events.py
CreditConsumedEvent        # Credits were used for an operation
CreditResetEvent          # Monthly credits reset
CreditLimitExceededEvent  # Credit limits exceeded

# models/pricing/events/subscription_events.py
SubscriptionChangedEvent   # Workspace tier changed
UsageLimitExceededEvent   # Monthly/rate limits hit
```

#### Domain Commands (Located in Domain Layer)

```python
# models/pricing/commands/credit_commands.py
DeductCreditsCommand           # Deduct credits from workspace
ResetMonthlyCreditsCommand     # Reset monthly credit allocation
PurchaseCreditsCommand         # Purchase additional credits

# models/pricing/commands/subscription_commands.py
ProcessSubscriptionChangeCommand # Change workspace tier
CancelSubscriptionCommand        # Cancel subscription
```

## Transactional Outbox Pattern

### Overview

VisionScope implements the **Transactional Outbox pattern** to ensure reliable event publishing with **ACID guarantees**. This enterprise pattern eliminates the dual-write problem and ensures that domain events are never lost, even in the face of system failures.

### Why Transactional Outbox?

- **Atomicity** - Events are saved in the same transaction as business data
- **Reliability** - No event loss due to messaging system failures
- **Consistency** - Event ordering and exactly-once delivery guarantees
- **Auditability** - Complete event history for compliance and debugging

### Architecture Components

#### 1. Event Outbox Model (`models/event_outbox.py`)

```python
class EventOutbox(Base):
    """Stores domain events for reliable publishing"""
    id: UUID
    event_type: str
    payload: dict
    published: bool = False
    published_at: datetime | None = None
    created_at: datetime
    correlation_id: UUID | None = None

    @classmethod
    def from_event(cls, event: IEvent) -> "EventOutbox":
        """Create outbox entry from domain event"""

    def mark_as_published(self) -> None:
        """Mark event as successfully published"""

    def reconstruct_event(self) -> IEvent:
        """Reconstruct original event from stored payload"""
```

#### 2. CQRS Operations (`building_blocks/messaging/outbox_cqrs.py`)

```python
class SaveEventToOutboxCommand(ICommand):
    """Save domain event to outbox table"""
    event: IEvent

class GetUnpublishedEventsQuery(IQuery[list[EventOutbox]]):
    """Retrieve events pending publication"""
    limit: int = 100

class MarkEventAsPublishedCommand(ICommand):
    """Mark event as successfully published"""
    event_id: UUID
```

#### 3. Pipeline Behavior (`building_blocks/behaviors/pipeline_behaviors.py`)

```python
class OutboxBehavior(IPipelineBehavior[TRequest, TResponse]):
    """Automatically saves domain events to outbox during command processing"""

    async def handle(
        self,
        request: TRequest,
        next_handler: RequestHandlerDelegate[TResponse]
    ) -> TResponse:
        # Execute business logic
        response = await next_handler(request)

        # Save any raised domain events to outbox
        if hasattr(request, 'events'):
            for event in request.events:
                await self._save_to_outbox(event)

        return response
```

#### 4. Background Publisher (`building_blocks/messaging/outbox_publisher.py`)

```python
class OutboxEventPublisher:
    """Background service for publishing events from outbox"""

    async def start_publishing(self) -> None:
        """Start background event publishing loop"""

    async def process_unpublished_events(self) -> None:
        """Process batch of unpublished events with retry logic"""

    def register_event_type(self, event_type: str, event_class: type[IEvent]) -> None:
        """Register event type for deserialization"""
```

### Usage Pattern

#### 1. Automatic Event Persistence

Events are automatically saved to the outbox when raised during command processing:

```python
class DeductCreditsHandler(ICommandHandler[DeductCreditsCommand, None]):
    async def handle(self, command: DeductCreditsCommand) -> None:
        # Business logic
        workspace.deduct_credits(command.amount)

        # Raise domain event (automatically saved to outbox)
        event = CreditDeductedEvent(
            workspace_id=workspace.id,
            amount=command.amount,
            remaining_credits=workspace.credits
        )
        command.events.append(event)  # OutboxBehavior handles persistence
```

#### 2. Background Publishing

```python
# Start the outbox publisher
publisher = OutboxEventPublisher(db_session, message_bus)
publisher.register_event_type("CreditDeductedEvent", CreditDeductedEvent)
await publisher.start_publishing()
```

### Enterprise Benefits

- **Zero Event Loss** - Events persisted transactionally with business data
- **Failure Recovery** - Unpublished events automatically retried
- **Monitoring** - Complete visibility into event publishing status
- **Debugging** - Full event history available in database
- **Compliance** - Audit trail for all domain events

## Message Flow Patterns

### 1. Credit Consumption Pattern

```
Video Analysis Request
    ↓
DeductCreditsCommand
    ↓
[Database Updates]
    ↓
CreditConsumedEvent → Analytics
                  → Billing
                  → Notifications
```

### 2. Subscription Change Pattern

```
Tier Upgrade Request
    ↓
ProcessSubscriptionChangeCommand
    ↓
[Complex FK Updates]
    ↓
SubscriptionChangedEvent → Credit Recalculation
                        → Feature Access Update
                        → Billing Cycle Change
```

## Queue Configuration

### Queue Strategy

- **`billing`** - High-priority revenue operations
- **`video_processing`** - GPU-intensive analysis tasks
- **`notifications`** - User communications
- **`default`** - General system operations

### Task Routing

```python
task_routes = {
    'billing.*': {'queue': 'billing'},
    'video_processing.*': {'queue': 'video_processing'},
    'notifications.*': {'queue': 'notifications'},
    'default': {'queue': 'default'}
}
```

## Implementation Examples

### Publishing Events

```python
from building_blocks import get_message_bus, CreditConsumedEvent

# After video analysis completes
event = CreditConsumedEvent(
    workspace_id=workspace.id,
    user_id=user.id,
    feature_code="video_analysis",
    credits_consumed=calculate_credits(video_length),
    processing_time_seconds=analysis_duration
)

message_bus = get_message_bus()
await message_bus.publish_event(event)
```

### Handling Commands

```python
@celery_app.task(name='billing.deduct_credits')
def deduct_credits_handler(command_data: str):
    command = deserialize_message(command_data, DeductCreditsCommand)

    with db_transaction():
        # 1. Update credits
        workspace_credit = update_workspace_credits(command)

        # 2. Create usage log
        create_usage_log(command)

        # 3. Check limits and publish events
        if workspace_credit.current_credits < 100:
            publish_event(LowCreditWarningEvent(...))
```

## Side Effect Coordination

### FK Relationship Management

The messaging system coordinates complex database updates across related tables:

- **Workspace tier changes** trigger credit recalculation across all features
- **Credit deduction** updates both workspace credits and usage logs
- **User collaboration** changes affect access control and billing responsibility

### Event Cascade Example

```
DeductCreditsCommand
    ├── Update WorkspaceCredit.current_credits
    ├── Update WorkspaceCredit.used_this_month
    ├── Create UsageLog entry
    ├── Check monthly limits
    └── Publish downstream events
        ├── CreditConsumedEvent (analytics)
        ├── UsageLimitExceededEvent (if needed)
        └── LowCreditWarningEvent (if needed)
```

## Monitoring & Operations

### Task Monitoring

- Celery Flower for real-time task monitoring
- Redis monitoring for queue depth and performance
- Custom metrics for business KPIs (credits/hour, revenue/day)

### Error Handling

- Automatic retries with exponential backoff
- Dead letter queues for failed messages
- Comprehensive logging for troubleshooting

### Scaling Strategy

- **Horizontal scaling** - Add more Celery workers
- **Queue prioritization** - Critical billing tasks first
- **Resource isolation** - Dedicated workers for GPU tasks

## Business Value

### Revenue Operations

- **Real-time billing** - No revenue leakage from untracked usage
- **Usage analytics** - Detailed insights for pricing optimization
- **Automated compliance** - Audit trail for all financial operations

### Investor Appeal

- **Scalable architecture** - Handles enterprise-scale operations
- **Revenue visibility** - Real-time tracking of money-making activities
- **Professional implementation** - Enterprise-grade messaging patterns

## Getting Started

### Initialization

```python
from building_blocks.messaging.celery_config import initialize_messaging

# Initialize messaging system
message_bus = initialize_messaging()
```

### Configuration

The messaging system is configured in `building_blocks/messaging/celery_config.py` with:

- Redis connection settings
- Task routing rules
- Queue definitions
- Worker configuration

### Development

- Use `get_message_bus()` to access the configured message bus
- Define new events/commands in `interfaces.py`
- Implement handlers in feature modules
- Register handlers with the message bus during initialization

---

**This messaging infrastructure is the foundation that transforms VisionScope from a video tool into a scalable SaaS revenue machine.** 🚀💰
