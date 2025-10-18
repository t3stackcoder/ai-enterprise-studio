"""
Building Blocks Test Builders

Extends infrastructure_testing.BaseTestBuilder to provide CQRS-specific
test object creation following the established infrastructure → domain pattern.
"""

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from building_blocks.context import ContextBuilder
from building_blocks.cqrs.interfaces import ICommand, ICommandWithResponse, IQuery
from building_blocks.cqrs.mediator import EnterpriseMediator
from infrastructure_testing.builders import BaseTestBuilder


# Test Commands and Queries for BB testing
@dataclass
class BBTestCreateUserCommand(ICommand):
    """Test command for BB testing"""

    username: str
    email: str

    def __post_init__(self):
        if not self.username or not self.email:
            raise ValueError("Username and email are required")


@dataclass
class BBTestGetUserQuery(IQuery[dict]):
    """Test query for BB testing"""

    user_id: str

    def get_cache_key(self) -> str:
        """Get cache key for this query"""
        return f"user:{self.user_id}"


@dataclass
class BBTestProcessPaymentCommand(ICommandWithResponse[str]):
    """Test command with response for BB testing"""

    amount: int
    user_id: str


class BBCommandBuilder(BaseTestBuilder):
    """
    Builder for creating CQRS commands and queries with context.
    Extends infrastructure BaseTestBuilder.
    """

    def __init__(self):
        super().__init__()
        self._context_builder = ContextBuilder()

    def create_user_command(
        self, username: str = "testuser", email: str = "test@example.com"
    ) -> BBTestCreateUserCommand:
        """Create a test user creation command"""
        command = BBTestCreateUserCommand(username=username, email=email)
        return self._apply_context(command)

    def get_user_query(self, user_id: str = "test_user_123") -> BBTestGetUserQuery:
        """Create a test user query"""
        query = BBTestGetUserQuery(user_id=user_id)
        return self._apply_context(query)

    def process_payment_command(
        self, amount: int = 100, user_id: str = "test_user"
    ) -> BBTestProcessPaymentCommand:
        """Create a test payment command"""
        command = BBTestProcessPaymentCommand(amount=amount, user_id=user_id)
        return self._apply_context(command)

    def with_user_context(
        self, user_id: str, roles: list[str] = None, permissions: set[str] = None
    ) -> "BBCommandBuilder":
        """Add user context to commands"""
        self._context_builder.with_user(user_id, roles or [], permissions or set())
        return self

    def with_workspace(self, workspace_id: str) -> "BBCommandBuilder":
        """Add workspace context"""
        self._context_builder.with_workspace(workspace_id)
        return self

    def with_transaction(self, requires_transaction: bool = True) -> "BBCommandBuilder":
        """Add transaction context"""
        self._context_builder.with_transaction(requires_transaction)
        return self

    def with_rate_limiting(self, rate_limit_key: str) -> "BBCommandBuilder":
        """Add rate limiting context"""
        self._context_builder.with_rate_limiting(rate_limit_key)
        return self

    def with_circuit_breaker(self, circuit_key: str) -> "BBCommandBuilder":
        """Add circuit breaker context"""
        self._context_builder.with_circuit_breaker(circuit_key)
        return self

    def with_caching(self, cache_key: str) -> "BBCommandBuilder":
        """Add caching context"""
        self._context_builder.with_caching(cache_key)
        return self

    def with_domain_events(self, events: list[Any]) -> "BBCommandBuilder":
        """Add domain events to be persisted via outbox"""
        # Store domain events directly in the builder for later application
        self._domain_events = events
        return self

    def _apply_context(self, request: Any) -> Any:
        """Apply built context to request"""
        context = self._context_builder.build()

        # Attach context attributes to request
        for attr_name, attr_value in context.__dict__.items():
            setattr(request, attr_name, attr_value)

        # Apply domain events if set
        if hasattr(self, "_domain_events"):
            request.domain_events = self._domain_events

        return request


class BBMediatorBuilder(BaseTestBuilder):
    """
    Builder for creating configured test mediators with handlers and behaviors.
    """

    def __init__(self):
        super().__init__()
        self._mediator = EnterpriseMediator()
        self._handlers = {}
        self._behaviors = []

    def with_test_handlers(self) -> "BBMediatorBuilder":
        """Add mock handlers for test commands/queries"""
        from infrastructure_testing.mocks import MockHandler

        # Register handlers for test commands
        self._mediator.register_command_handler(BBTestCreateUserCommand, MockHandler())
        self._mediator.register_query_handler(
            BBTestGetUserQuery, MockHandler(response={"user_id": "123", "username": "test"})
        )
        self._mediator.register_command_with_response_handler(
            BBTestProcessPaymentCommand, MockHandler(response="payment_123")
        )

        return self

    def with_validation_behavior(self) -> "BBMediatorBuilder":
        """Add validation pipeline behavior"""
        from building_blocks.behaviors.pipeline_behaviors import ValidationBehavior

        self._mediator.add_pipeline_behavior(ValidationBehavior())
        return self

    def with_logging_behavior(self, slow_threshold: float = 1.0) -> "BBMediatorBuilder":
        """Add logging pipeline behavior"""
        from building_blocks.behaviors.pipeline_behaviors import LoggingBehavior

        self._mediator.add_pipeline_behavior(LoggingBehavior(slow_threshold=slow_threshold))
        return self

    def with_authorization_behavior(self) -> "BBMediatorBuilder":
        """Add authorization pipeline behavior"""
        from building_blocks.behaviors.pipeline_behaviors import AuthorizationBehavior

        self._mediator.add_pipeline_behavior(AuthorizationBehavior())
        return self

    def with_transaction_behavior(self) -> "BBMediatorBuilder":
        """Add transaction pipeline behavior"""
        from building_blocks.behaviors.pipeline_behaviors import TransactionBehavior

        self._mediator.add_pipeline_behavior(TransactionBehavior())
        return self

    def with_outbox_behavior(self) -> "BBMediatorBuilder":
        """Add outbox pipeline behavior"""
        from building_blocks.behaviors.pipeline_behaviors import OutboxBehavior

        outbox_behavior = OutboxBehavior(mediator=self._mediator)
        self._mediator.add_pipeline_behavior(outbox_behavior)
        return self

    def build(self) -> EnterpriseMediator:
        """Build the configured mediator"""
        return self._mediator


class BBPipelineBuilder(BaseTestBuilder):
    """
    Builder for creating pipeline test scenarios.
    """

    def __init__(self):
        super().__init__()
        self._behaviors = []
        self._request = None

    def with_validation_behavior(self) -> "BBPipelineBuilder":
        """Add validation behavior to pipeline"""
        from building_blocks.behaviors.pipeline_behaviors import ValidationBehavior

        self._behaviors.append(ValidationBehavior())
        return self

    def with_authorization_behavior(self) -> "BBPipelineBuilder":
        """Add authorization behavior to pipeline"""
        from building_blocks.behaviors.pipeline_behaviors import AuthorizationBehavior

        self._behaviors.append(AuthorizationBehavior())
        return self

    def with_request(self, request: Any) -> "BBPipelineBuilder":
        """Set the request for pipeline testing"""
        self._request = request
        return self

    async def execute_with_mock_handler(self, mock_response: Any = "success") -> Any:
        """Execute pipeline with mock final handler"""
        from unittest.mock import AsyncMock

        if not self._request:
            raise ValueError("Request must be set before execution")

        final_handler = AsyncMock(return_value=mock_response)

        # Build pipeline chain (reverse order)
        current_handler = final_handler
        for behavior in reversed(self._behaviors):
            next_handler = current_handler

            async def create_handler(beh=behavior, nh=next_handler):
                return await beh.handle(self._request, nh)

            current_handler = create_handler

        return await current_handler()


class BBOutboxBuilder(BaseTestBuilder):
    """
    Builder for creating outbox test scenarios.
    """

    def __init__(self):
        super().__init__()
        self._events = []
        self._correlation_id = str(uuid4())

    def with_domain_event(self, event_type: str = "TestEvent", **event_data) -> "BBOutboxBuilder":
        """Add a domain event to the scenario"""
        from infrastructure_testing.mocks import MockDomainEvent

        event = MockDomainEvent(event_type=event_type, **event_data)
        event.correlation_id = self._correlation_id
        self._events.append(event)
        return self

    def with_correlation_id(self, correlation_id: str) -> "BBOutboxBuilder":
        """Set correlation ID for events"""
        self._correlation_id = correlation_id
        for event in self._events:
            event.correlation_id = correlation_id
        return self

    def build_command_with_events(self) -> BBTestCreateUserCommand:
        """Build a command with domain events attached"""
        command = BBTestCreateUserCommand(username="testuser", email="test@example.com")
        command.domain_events = self._events
        command.correlation_id = self._correlation_id
        return command

    def build_events(self) -> list[Any]:
        """Build just the events list"""
        return self._events.copy()
