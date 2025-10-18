"""
Context and Exception Handling Tests

Tests RequestContext handling, context attachment to requests, exception propagation
through the pipeline, and proper error handling across all building blocks components.
"""

from uuid import uuid4

import pytest
from building_blocks.context import (
    ContextBuilder,
    RequestContext,
    get_context_from_request,
    with_context,
)
from building_blocks.exceptions.pipeline_exceptions import (
    AuthorizationPipelineException,
    HandlerNotFoundException,
    TransactionPipelineException,
    ValidationPipelineException,
)

from .builders import BBCommandBuilder, BBTestCreateUserCommand


class TestRequestContext:
    """Test RequestContext creation and manipulation"""

    def test_request_context_builder_creates_context_with_user_info(self):
        """REAL TEST: ContextBuilder creates context with user information"""
        # Given: Context builder
        builder = ContextBuilder()

        # When: Build context with user info
        context = (
            builder.with_user("user123", roles=["admin", "user"], permissions={"read", "write"})
            .with_workspace("workspace456")
            .with_transaction(requires_transaction=True, auto_commit=False)
            .build()
        )

        # Then: Context should have all specified information
        assert context.user_id == "user123"
        assert context.user_roles == ["admin", "user"]
        assert context.permissions == {"read", "write"}
        assert context.workspace_id == "workspace456"
        assert context.requires_transaction is True
        assert context.auto_commit is False
        assert context.correlation_id is not None  # Auto-generated

    def test_request_context_has_default_values(self):
        """REAL TEST: RequestContext has sensible defaults"""
        # Given: Default context
        context = RequestContext()

        # Then: Should have default values
        assert context.correlation_id is not None
        assert context.user_context is None
        assert context.db_session is None
        assert context.workspace_id is None
        assert context.user_id is None
        assert context.user_roles == []
        assert context.permissions == set()
        assert context.requires_transaction is False
        assert context.auto_commit is True

    def test_context_builder_with_performance_settings(self):
        """REAL TEST: Context builder supports performance settings"""
        # Given: Context builder
        builder = ContextBuilder()

        # When: Build context with performance settings
        context = (
            builder.with_rate_limiting("user_123_api_calls")
            .with_circuit_breaker("payment_service")
            .with_caching("user_profile_123")
            .build()
        )

        # Then: Context should have performance settings
        assert context.rate_limit_key == "user_123_api_calls"
        assert context.circuit_breaker_key == "payment_service"
        assert context.cache_key == "user_profile_123"


class TestContextAttachment:
    """Test attaching context to requests"""

    def test_with_context_attaches_context_to_request(self):
        """REAL TEST: with_context attaches all context attributes to request"""
        # Given: Command and context
        command = BBTestCreateUserCommand(username="test", email="test@example.com")
        context = (
            ContextBuilder()
            .with_user("user123", roles=["admin"])
            .with_workspace("workspace456")
            .with_transaction(requires_transaction=True)
            .build()
        )

        # When: Attach context to command
        command_with_context = with_context(command, context)

        # Then: Command should have all context attributes
        assert command_with_context.user_id == "user123"
        assert command_with_context.user_roles == ["admin"]
        assert command_with_context.workspace_id == "workspace456"
        assert command_with_context.requires_transaction is True
        assert command_with_context.correlation_id == context.correlation_id
        assert command_with_context.username == "test"  # Original attributes preserved
        assert command_with_context.email == "test@example.com"

    def test_get_context_from_request_extracts_context(self):
        """REAL TEST: get_context_from_request extracts context from request"""
        # Given: Command with attached context
        command = BBTestCreateUserCommand(username="test", email="test@example.com")
        command.user_id = "user123"
        command.workspace_id = "workspace456"
        command.requires_transaction = True
        command.correlation_id = uuid4()

        # When: Extract context from command
        extracted_context = get_context_from_request(command)

        # Then: Context should have extracted values
        assert extracted_context.user_id == "user123"
        assert extracted_context.workspace_id == "workspace456"
        assert extracted_context.requires_transaction is True
        assert extracted_context.correlation_id == command.correlation_id

    def test_bb_command_builder_applies_context_to_commands(self):
        """REAL TEST: BBCommandBuilder applies context to created commands"""
        # Given: Command builder with context
        builder = BBCommandBuilder()

        # When: Create command with context
        command = (
            builder.with_user_context("user123", roles=["admin"], permissions={"create_user"})
            .with_workspace("workspace456")
            .with_transaction(requires_transaction=True)
            .with_rate_limiting("user_123")
            .create_user_command(username="contexttest", email="context@example.com")
        )

        # Then: Command should have context applied
        assert command.user_id == "user123"
        assert command.user_roles == ["admin"]
        assert command.permissions == {"create_user"}
        assert command.workspace_id == "workspace456"
        assert command.requires_transaction is True
        assert command.rate_limit_key == "user_123"
        assert command.username == "contexttest"
        assert command.email == "context@example.com"


class TestExceptionHandling:
    """Test exception handling and propagation"""

    def test_handler_not_found_exception_contains_request_type(self):
        """REAL TEST: HandlerNotFoundException provides clear error information"""
        # Given: Exception for missing handler
        exception = HandlerNotFoundException(BBTestCreateUserCommand)

        # Then: Exception should contain helpful information
        assert "BBTestCreateUserCommand" in str(exception)
        assert exception.request_type_class == BBTestCreateUserCommand

    def test_validation_pipeline_exception_contains_validation_errors(self):
        """REAL TEST: ValidationPipelineException provides validation details"""
        # Given: Validation errors
        validation_errors = ["Username is required", "Email format is invalid"]
        inner_exception = ValueError("Validation failed")

        exception = ValidationPipelineException(
            request_type="BBTestCreateUserCommand",
            validation_errors=validation_errors,
            inner_exception=inner_exception,
        )

        # Then: Exception should contain all validation details
        assert "BBTestCreateUserCommand" in str(exception)
        assert "Username is required" in str(exception)
        assert "Email format is invalid" in str(exception)
        assert exception.validation_errors == validation_errors
        assert exception.inner_exception == inner_exception
        assert exception.behavior_type == "ValidationBehavior"

    def test_authorization_pipeline_exception_contains_user_info(self):
        """REAL TEST: AuthorizationPipelineException provides authorization context"""
        # Given: Authorization failure
        exception = AuthorizationPipelineException(
            request_type="BBTestCreateUserCommand",
            user_id="user123",
            required_permission="create_user",
        )

        # Then: Exception should contain authorization details
        assert "BBTestCreateUserCommand" in str(exception)
        assert "user123" in str(exception)
        assert "create_user" in str(exception)
        assert exception.user_id == "user123"
        assert exception.required_permission == "create_user"
        assert exception.behavior_type == "AuthorizationBehavior"

    def test_transaction_pipeline_exception_contains_operation_info(self):
        """REAL TEST: TransactionPipelineException provides transaction context"""
        # Given: Transaction failure
        inner_exception = Exception("Database connection lost")
        exception = TransactionPipelineException(
            request_type="BBTestCreateUserCommand",
            operation="rollback",
            inner_exception=inner_exception,
        )

        # Then: Exception should contain transaction details
        assert "BBTestCreateUserCommand" in str(exception)
        assert "rollback" in str(exception)
        assert exception.operation == "rollback"
        assert exception.inner_exception == inner_exception
        assert exception.behavior_type == "TransactionBehavior"


class TestExceptionPropagation:
    """Test exception propagation through pipeline"""

    @pytest.mark.asyncio
    async def test_pipeline_exception_propagates_with_context(self):
        """REAL TEST: Exceptions propagate with request context preserved"""
        # Given: Pipeline behavior that will fail
        from unittest.mock import AsyncMock

        from building_blocks.behaviors.pipeline_behaviors import ValidationBehavior
        from pydantic import BaseModel, field_validator

        class InvalidCommand(BaseModel):
            required_field: str
            age: int

            @field_validator("age")
            @classmethod
            def validate_age(cls, v):
                if v < 0:
                    raise ValueError("Age cannot be negative")
                return v

        validation_behavior = ValidationBehavior()

        # Create valid command then modify to be invalid
        invalid_command = InvalidCommand(required_field="test", age=25)
        invalid_command.__dict__["age"] = -5  # Make it invalid

        mock_handler = AsyncMock(return_value="should_not_execute")

        # When: Execute through validation behavior
        # Then: Should raise ValidationPipelineException with context
        with pytest.raises(ValidationPipelineException) as exc_info:
            await validation_behavior.handle(invalid_command, mock_handler)

        exception = exc_info.value
        assert "InvalidCommand" in str(exception)
        assert exception.behavior_type == "ValidationBehavior"

    @pytest.mark.asyncio
    async def test_mediator_wraps_handler_exceptions_in_pipeline_exception(self):
        """REAL TEST: Mediator wraps handler exceptions with context"""
        # Given: Mediator with handler that throws exception
        from building_blocks.cqrs.mediator import EnterpriseMediator
        from building_blocks.exceptions.pipeline_exceptions import PipelineExecutionException
        from infrastructure_testing.mocks import MockHandler

        mediator = EnterpriseMediator()

        # Handler that always fails
        failing_handler = MockHandler(should_raise=Exception("Handler execution failed"))
        mediator.register_command_handler(BBTestCreateUserCommand, failing_handler)

        # When: Send command to failing handler
        command = BBTestCreateUserCommand(username="test", email="test@example.com")

        # Then: Should wrap exception with pipeline context
        with pytest.raises(PipelineExecutionException) as exc_info:
            await mediator.send_command(command)

        exception = exc_info.value
        assert "BBTestCreateUserCommand" in str(exception)
        assert "CommandExecution" in str(exception)
        assert "Handler execution failed" in str(exception)


class TestCorrelationIdTracking:
    """Test correlation ID tracking through pipeline"""

    def test_correlation_id_flows_through_context(self):
        """REAL TEST: Correlation ID flows through request context"""
        # Given: Context with correlation ID
        correlation_id = uuid4()
        context = ContextBuilder().with_correlation_id(correlation_id).build()

        # When: Attach to command
        command = BBTestCreateUserCommand(username="test", email="test@example.com")
        command_with_context = with_context(command, context)

        # Then: Correlation ID should be preserved
        assert command_with_context.correlation_id == correlation_id

    def test_bb_command_builder_preserves_correlation_id(self):
        """REAL TEST: BBCommandBuilder preserves correlation ID through operations"""
        # Given: Builder with correlation ID
        correlation_id = uuid4()
        builder = BBCommandBuilder()
        builder._context_builder.with_correlation_id(correlation_id)

        # When: Create command
        command = builder.create_user_command(username="corrtest", email="corr@example.com")

        # Then: Command should have correlation ID
        assert command.correlation_id == correlation_id

    def test_context_builder_generates_correlation_id_if_not_provided(self):
        """REAL TEST: ContextBuilder auto-generates correlation ID"""
        # Given: Context builder without explicit correlation ID
        builder = ContextBuilder()

        # When: Build context
        context = builder.build()

        # Then: Should auto-generate correlation ID
        assert context.correlation_id is not None
        assert isinstance(context.correlation_id, type(uuid4()))
