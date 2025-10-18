# Enterprise CQRS Building Blocks Architecture

## Overview

VisionScope implements **Enterprise-grade Command Query Responsibility Segregation (CQRS)** patterns with advanced resilience features, providing bulletproof foundations for scalable business logic. These building blocks deliver production-ready patterns with enterprise observability, error handling, and performance optimization.

## Why Enterprise CQRS for VisionScope?

### Business Complexity

- **Billing operations** require ACID transactions with audit trails
- **Video analysis** involves GPU-intensive multi-step processing pipelines
- **Usage tracking** needs real-time credit deduction with billing consistency
- **Multi-tenant workspaces** require isolated data operations with rate limiting
- **Enterprise customers** demand 99.9% uptime with comprehensive monitoring

### Enterprise Architecture Benefits

- **Separation of Concerns** - Commands modify state, queries read state
- **Scalability** - Read and write sides scale independently with horizontal partitioning
- **Resilience** - Circuit breakers, retries, and dead letter queues for fault tolerance
- **Observability** - Distributed tracing, performance monitoring, and audit logging
- **Security** - Built-in authorization, rate limiting, and validation pipelines
- **Testability** - Business logic isolated in handlers with comprehensive mocking support
- **Maintainability** - Clear boundaries with enterprise design patterns

## Core Components

### 1. Enterprise Interfaces (`building_blocks/cqrs/interfaces.py`)

#### Commands (Write Operations)

```python
class ICommand(ABC):
    """Marker interface for commands with validation support"""
    @abstractmethod
    def __post_init__(self) -> None:
        """Commands must implement validation if needed"""
        pass

class ICommandHandler(ABC, Generic[TCommand]):
    """Handles a specific command type with enterprise patterns"""
    @abstractmethod
    async def handle(self, command: TCommand) -> None:
        """Handle command with full pipeline support"""
        pass

class ICommandWithResponse(Generic[TResponse], ABC):
    """Command interface that returns a response"""
    pass
```

#### Queries (Read Operations)

```python
class IQuery(Generic[TResponse], ABC):
    """Base interface for queries with caching support"""
    pass

class IQueryHandler(ABC, Generic[TQuery, TResponse]):
    """Handles queries with performance optimization"""
    @abstractmethod
    async def handle(self, query: TQuery) -> TResponse:
        """Handle query with caching and monitoring"""
        pass
```

### 2. Enterprise Mediator Pattern (`building_blocks/cqrs/mediator.py`)

Enterprise-grade coordination with pipeline behaviors and fault tolerance:

```python
class IMediator(ABC):
    """Enterprise mediator with pipeline support"""
    @abstractmethod
    async def send_command(self, command: ICommand) -> None:
        """Send command through enterprise pipeline"""
        pass

    @abstractmethod
    async def send_command_with_response(
        self, command: ICommandWithResponse[TResponse]
    ) -> TResponse:
        """Send command with response through enterprise pipeline"""
        pass

    @abstractmethod
    async def send_query(self, query: IQuery[TResponse]) -> TResponse:
        """Send query through enterprise pipeline with caching"""
        pass

    @abstractmethod
    def add_pipeline_behavior(self, behavior: IPipelineBehavior) -> None:
        """Add enterprise pipeline behavior"""
        pass

class EnterpriseMediator(IMediator):
    """Production-ready mediator with full enterprise features"""
    # Supports pipeline behaviors, dependency injection, and monitoring
```

**Enterprise Benefits:**

- **Decoupling** - Controllers never know about specific handlers
- **Pipeline Behaviors** - Automatic validation, logging, auth, caching, circuit breakers
- **Fault Tolerance** - Built-in retry logic and error handling
- **Observability** - Distributed tracing and performance monitoring
- **Security** - Authorization and rate limiting built-in

### 3. Enterprise Pipeline Behaviors (`building_blocks/behaviors/`)

Production-ready cross-cutting concerns applied to all commands/queries:

```python
class ValidationBehavior(IPipelineBehavior):
    """Enterprise validation with detailed error reporting"""
    # - Pydantic validation with constraint checking
    # - Custom validation hooks for complex business rules
    # - Detailed error messages with field-level feedback

class LoggingBehavior(IPipelineBehavior):
    """Enterprise logging with performance monitoring"""
    # - Correlation ID tracking for distributed tracing
    # - Performance monitoring with configurable thresholds
    # - Structured logging for enterprise observability

class AuthorizationBehavior(IPipelineBehavior):
    """Role-based access control with workspace isolation"""
    # - User context validation and role checking
    # - Workspace-level access control
    # - Custom authorization hooks for complex permissions

class TransactionBehavior(IPipelineBehavior):
    """Database transaction management with automatic rollback"""
    # - Automatic transaction boundaries for commands
    # - Rollback on failure with detailed error logging
    # - Configurable auto-commit behavior

class CachingBehavior(IPipelineBehavior):
    """Intelligent caching with TTL and invalidation"""
    # - Query result caching with configurable TTL
    # - Cache invalidation strategies
    # - Performance optimization for read-heavy operations

class RateLimitingBehavior(IPipelineBehavior):
    """Per-user and per-workspace rate limiting"""
    # - Sliding window rate limiting
    # - Configurable limits per feature
    # - Integration with billing tier restrictions

class CircuitBreakerBehavior(IPipelineBehavior):
    """Fault tolerance for external service calls"""
    # - Automatic failure detection and recovery
    # - Configurable failure thresholds
    # - Graceful degradation patterns

class OutboxBehavior(IPipelineBehavior):
    """Transactional Outbox pattern for reliable event publishing"""
    # - Saves domain events transactionally with business data
    # - Ensures no event loss due to messaging system failures
    # - Automatic event persistence during command processing
    # - Integration with background event publisher
```

### 4. Domain Exceptions (`building_blocks/exceptions/`)

Enterprise-grade error handling with detailed context:

```python
class DomainException(Exception):
    """Base for all business logic errors with rich context"""

class NotFoundException(DomainException):
    """Entity not found with specific identifier details"""

class ValidationException(DomainException):
    """Validation failed with field-level error details"""

class UnauthorizedException(DomainException):
    """Unauthorized access with operation context"""

class DuplicateEntityException(DomainException):
    """Entity already exists with conflict resolution guidance"""
```

## Enterprise Setup and Configuration

### Quick Start with Enterprise Features

```python
from building_blocks import (
    EnterpriseMediator,
    EnterpriseMessageBus,
    ValidationBehavior,
    LoggingBehavior,
    AuthorizationBehavior,
    TransactionBehavior
)

# Configure enterprise mediator
mediator = EnterpriseMediator()

# Add enterprise pipeline behaviors
mediator.add_pipeline_behavior(ValidationBehavior())
mediator.add_pipeline_behavior(LoggingBehavior(slow_threshold=2.0))
mediator.add_pipeline_behavior(AuthorizationBehavior())
mediator.add_pipeline_behavior(TransactionBehavior(auto_commit=True))

# Configure enterprise message bus
message_bus = EnterpriseMessageBus(
    celery_app=celery_app,
    retry_policy=ExponentialBackoffRetryPolicy(max_retries=3),
    dead_letter_queue=CeleryDeadLetterQueue(),
    tracer=OpenTelemetryTracer()
)

# Set as global instances
configure_mediator(mediator)
configure_message_bus(celery_app, use_enterprise=True)
```

### Domain Organization

Enterprise building blocks enforce clean domain separation:

```
models/pricing/
├── events/
│   ├── credit_events.py      # CreditConsumedEvent, CreditResetEvent
│   └── subscription_events.py # SubscriptionChangedEvent, etc.
├── commands/
│   ├── credit_commands.py     # DeductCreditsCommand, etc.
│   └── subscription_commands.py # ProcessSubscriptionChangeCommand
└── handlers/
    ├── credit_handlers.py     # Business logic implementation
    └── subscription_handlers.py
```

**Key Principle:** Building blocks contain ZERO domain knowledge - they're pure infrastructure!

## Implementation Patterns

### Enterprise Command Pattern Example

```python
# 1. Define the command (in domain layer)
class ProcessVideoCommand(ICommand):
    """Command with enterprise features"""
    workspace_id: UUID
    video_file: str
    analysis_type: str
    user_id: UUID

    # Enterprise features
    user_context: UserContext | None = None
    requires_transaction: bool = True
    rate_limit_key: str = None

    def __post_init__(self):
        """Validation hook called by ValidationBehavior"""
        if not self.workspace_id:
            raise ValueError("workspace_id is required")
        self.rate_limit_key = f"video_processing:{self.workspace_id}"

# 2. Implement the enterprise handler
class ProcessVideoHandler(ICommandHandler[ProcessVideoCommand]):
    def __init__(self,
                 video_service: VideoService,
                 billing_service: BillingService,
                 db_session: DatabaseSession):
        self.video_service = video_service
        self.billing_service = billing_service
        self.db_session = db_session

    async def handle(self, command: ProcessVideoCommand) -> None:
        """Handler with enterprise pipeline support"""
        # Pipeline behaviors automatically handle:
        # - Validation (ValidationBehavior)
        # - Authorization (AuthorizationBehavior)
        # - Rate limiting (RateLimitingBehavior)
        # - Transaction management (TransactionBehavior)
        # - Performance monitoring (LoggingBehavior)

        # Business logic
        credits_required = await self.billing_service.calculate_credits(
            command.analysis_type
        )

        # Deduct credits (will publish CreditConsumedEvent)
        await self.billing_service.deduct_credits(
            command.workspace_id,
            credits_required,
            command.user_id
        )

        # Process video with circuit breaker protection
        result = await self.video_service.analyze_with_circuit_breaker(
            command.video_file,
            command.analysis_type
        )

        # Process video
        result = await self.video_service.analyze(
            command.video_file,
            command.analysis_type
        )

        # Deduct credits
        await self.billing_service.deduct_credits(
            command.workspace_id,
            result.credits_used
        )

        return result

# 3. Use through mediator
mediator = get_mediator()
result = await mediator.send_command(ProcessVideoCommand(...))
```

### Query Pattern Example

```python
# 1. Define the query
class GetWorkspaceUsageQuery(IQuery):
    workspace_id: UUID
    start_date: datetime
    end_date: datetime

# 2. Implement the handler
class GetWorkspaceUsageHandler(IQueryHandler[GetWorkspaceUsageQuery]):
    def __init__(self, usage_repository: UsageRepository):
        self.usage_repository = usage_repository

    async def handle(self, query: GetWorkspaceUsageQuery) -> UsageReport:
        return await self.usage_repository.get_usage_report(
            query.workspace_id,
            query.start_date,
            query.end_date
        )

# 3. Use through mediator
usage_report = await mediator.send_query(GetWorkspaceUsageQuery(...))
```

## Integration with Messaging

CQRS commands can trigger events through the messaging system:

```python
class DeductCreditsHandler(ICommandHandler[DeductCreditsCommand]):
    def __init__(self,
                 credit_repository: CreditRepository,
                 message_bus: IMessageBus):
        self.credit_repository = credit_repository
        self.message_bus = message_bus

    async def handle(self, command: DeductCreditsCommand) -> None:
        # Update database
        credits_remaining = await self.credit_repository.deduct_credits(
            command.workspace_id,
            command.credits_to_deduct
        )

        # Publish event for downstream processing
        event = CreditConsumedEvent(
            workspace_id=command.workspace_id,
            credits_consumed=command.credits_to_deduct,
            feature_code=command.feature_code
        )
        await self.message_bus.publish_event(event)
```

## FastAPI Integration

CQRS integrates seamlessly with FastAPI endpoints:

```python
@app.post("/workspaces/{workspace_id}/videos")
async def upload_video(
    workspace_id: UUID,
    video: UploadFile,
    analysis_type: str,
    mediator: IMediator = Depends(get_mediator),
    current_user: User = Depends(get_current_user)
):
    command = ProcessVideoCommand(
        workspace_id=workspace_id,
        video_file=video.filename,
        analysis_type=analysis_type,
        user_id=current_user.user_id
    )

    try:
        result = await mediator.send_command(command)
        return {"status": "success", "result": result}
    except InsufficientCreditsException:
        raise HTTPException(
            status_code=402,
            detail="Insufficient credits for this operation"
        )
```

## Error Handling Strategy

### Domain Exceptions

Business logic errors are handled through domain exceptions:

```python
class WorkspaceNotFoundError(DomainException):
    def __init__(self, workspace_id: UUID):
        super().__init__(f"Workspace {workspace_id} not found")

class InsufficientCreditsError(DomainException):
    def __init__(self, required: int, available: int):
        super().__init__(f"Need {required} credits, only {available} available")
```

### Pipeline Error Handling

Behaviors can catch and transform errors:

```python
class ErrorHandlingBehavior(IPipelineBehavior):
    async def handle(self, request, next_handler):
        try:
            return await next_handler(request)
        except DomainException as e:
            logger.error(f"Domain error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise UnexpectedError("An unexpected error occurred")
```

## Testing Strategy

### Unit Testing Commands

```python
async def test_process_video_deducts_credits():
    # Arrange
    handler = ProcessVideoHandler(mock_video_service, mock_billing_service)
    command = ProcessVideoCommand(
        workspace_id=test_workspace_id,
        video_file="test.mp4",
        analysis_type="emotion"
    )

    # Act
    await handler.handle(command)

    # Assert
    mock_billing_service.deduct_credits.assert_called_once()
```

### Integration Testing with Mediator

```python
async def test_full_video_processing_flow():
    # Test the complete flow through mediator
    result = await mediator.send_command(ProcessVideoCommand(...))
    assert result.status == "success"
```

## Performance Considerations

### Async/Await

All handlers use async/await for non-blocking operations:

- Database queries don't block other requests
- External API calls are concurrent
- Video processing can be backgrounded

### Enterprise Caching Strategy

Queries leverage intelligent caching with the CachingBehavior:

```python
class GetWorkspaceUsageQuery(IQuery[WorkspaceUsageReport]):
    workspace_id: UUID
    date_range: DateRange

    @property
    def cache_key(self) -> str:
        """Cache key for CachingBehavior"""
        return f"workspace_usage:{self.workspace_id}:{self.date_range.hash}"

class GetWorkspaceUsageHandler(IQueryHandler[GetWorkspaceUsageQuery, WorkspaceUsageReport]):
    async def handle(self, query: GetWorkspaceUsageQuery) -> WorkspaceUsageReport:
        # CachingBehavior automatically handles:
        # - Cache key generation
        # - TTL management
        # - Cache invalidation
        return await self.usage_service.get_report(query.workspace_id, query.date_range)
```

## Enterprise Business Value

### Development Velocity

- **Enterprise patterns** - Proven patterns reduce decision fatigue
- **Built-in quality** - Pipeline behaviors ensure consistent quality
- **Zero-config observability** - Automatic tracing and monitoring
- **Type safety** - Comprehensive type hints catch bugs early

### Production Reliability

- **Fault tolerance** - Circuit breakers and retry logic built-in
- **Performance optimization** - Automatic caching and monitoring
- **Security by default** - Authorization and validation enforced
- **Audit compliance** - Complete audit trails for all operations

### Enterprise Scalability

- **Horizontal scaling** - Message bus scales workers automatically
- **Independent scaling** - Read/write operations scale separately
- **Resource optimization** - Intelligent caching and rate limiting
- **Cost optimization** - Usage tracking for accurate billing

## Migration from Legacy

### Backward Compatibility

The enterprise building blocks maintain 100% backward compatibility:

```python
# Legacy code still works
from building_blocks import Mediator, CeleryMessageBus

# But new code should use enterprise versions
from building_blocks import EnterpriseMediator, EnterpriseMessageBus
```

### Upgrade Path

1. **Replace mediator**: `Mediator` → `EnterpriseMediator`
2. **Add pipeline behaviors**: Start with `ValidationBehavior` and `LoggingBehavior`
3. **Replace message bus**: `CeleryMessageBus` → `EnterpriseMessageBus`
4. **Move domain events**: From `building_blocks/messaging` to `models/*/events/`
5. **Add enterprise behaviors**: Authorization, caching, rate limiting as needed

---

**These enterprise building blocks transform VisionScope from a video tool into a scalable SaaS revenue machine.** 🚀💰

---

**CQRS Building Blocks provide the clean architecture foundation that makes VisionScope maintainable, testable, and scalable for enterprise growth.** 🚀
