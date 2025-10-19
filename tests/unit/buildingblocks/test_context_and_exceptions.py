"""
Unit tests for Context, Exceptions, and Remaining Pipeline Behaviors
"""

import pytest
from uuid import UUID, uuid4

from libs.buildingblocks.context import (
    ContextBuilder,
    RequestContext,
    get_context_from_request,
    with_context,
)
from libs.buildingblocks.cqrs.interfaces import ICommand
from libs.buildingblocks.exceptions.domain_exceptions import (
    DomainException,
    DuplicateEntityException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from libs.buildingblocks.exceptions.pipeline_exceptions import (
    AuthorizationPipelineException,
    CircuitBreakerOpenException,
    HandlerNotFoundException,
    HandlerRegistrationException,
    PipelineException,
    PipelineExecutionException,
    RateLimitExceededException,
    TransactionPipelineException,
    ValidationPipelineException,
)


# ============================================================================
# RequestContext Tests
# ============================================================================


@pytest.mark.unit
def test_request_context_has_default_values():
    """
    Test that RequestContext initializes with sensible defaults.
    """
    context = RequestContext()

    assert isinstance(context.correlation_id, UUID)
    assert context.user_context is None
    assert context.db_session is None
    assert context.workspace_id is None
    assert context.metadata == {}
    assert context.user_roles == []
    assert context.permissions == set()
    assert context.requires_transaction is False
    print("✅ RequestContext has default values")


@pytest.mark.unit
def test_request_context_can_be_created_with_values():
    """
    Test that RequestContext can be created with custom values.
    """
    correlation_id = uuid4()
    context = RequestContext(
        correlation_id=correlation_id,
        user_id="user-123",
        workspace_id="workspace-456",
        requires_transaction=True,
    )

    assert context.correlation_id == correlation_id
    assert context.user_id == "user-123"
    assert context.workspace_id == "workspace-456"
    assert context.requires_transaction is True
    print("✅ RequestContext created with custom values")


@pytest.mark.unit
def test_with_context_attaches_context_to_request():
    """
    Test that with_context attaches all context attributes to request.
    """

    class TestCommand(ICommand):
        pass

    command = TestCommand()
    context = RequestContext(
        user_id="user-123", workspace_id="workspace-456", rate_limit_key="test-key"
    )

    result = with_context(command, context)

    assert result is command  # Same object
    assert hasattr(command, "user_id")
    assert command.user_id == "user-123"
    assert command.workspace_id == "workspace-456"
    assert command.rate_limit_key == "test-key"
    print("✅ with_context attached context to request")


@pytest.mark.unit
def test_get_context_from_request_extracts_context():
    """
    Test that get_context_from_request extracts RequestContext from request.
    """

    class TestCommand(ICommand):
        def __init__(self):
            self.user_id = "user-123"
            self.workspace_id = "workspace-456"
            self.requires_transaction = True

    command = TestCommand()
    context = get_context_from_request(command)

    assert isinstance(context, RequestContext)
    assert context.user_id == "user-123"
    assert context.workspace_id == "workspace-456"
    assert context.requires_transaction is True
    print("✅ get_context_from_request extracted context")


# ============================================================================
# ContextBuilder Tests
# ============================================================================


@pytest.mark.unit
def test_context_builder_builds_empty_context():
    """
    Test that ContextBuilder can build empty context.
    """
    builder = ContextBuilder()
    context = builder.build()

    assert isinstance(context, RequestContext)
    assert context.user_id is None
    print("✅ ContextBuilder built empty context")


@pytest.mark.unit
def test_context_builder_with_user():
    """
    Test that ContextBuilder.with_user sets user information.
    """
    context = (
        ContextBuilder()
        .with_user("user-123", roles=["admin", "user"], permissions={"read", "write"})
        .build()
    )

    assert context.user_id == "user-123"
    assert context.user_roles == ["admin", "user"]
    assert context.permissions == {"read", "write"}
    print("✅ ContextBuilder.with_user worked")


@pytest.mark.unit
def test_context_builder_with_workspace():
    """
    Test that ContextBuilder.with_workspace sets workspace ID.
    """
    context = ContextBuilder().with_workspace("workspace-456").build()

    assert context.workspace_id == "workspace-456"
    print("✅ ContextBuilder.with_workspace worked")


@pytest.mark.unit
def test_context_builder_with_transaction():
    """
    Test that ContextBuilder.with_transaction sets transaction info.
    """
    context = ContextBuilder().with_transaction(requires_transaction=True, auto_commit=False).build()

    assert context.requires_transaction is True
    assert context.auto_commit is False
    print("✅ ContextBuilder.with_transaction worked")


@pytest.mark.unit
def test_context_builder_with_rate_limiting():
    """
    Test that ContextBuilder.with_rate_limiting sets rate limit key.
    """
    context = ContextBuilder().with_rate_limiting("user-123").build()

    assert context.rate_limit_key == "user-123"
    print("✅ ContextBuilder.with_rate_limiting worked")


@pytest.mark.unit
def test_context_builder_with_circuit_breaker():
    """
    Test that ContextBuilder.with_circuit_breaker sets circuit breaker key.
    """
    context = ContextBuilder().with_circuit_breaker("service-a").build()

    assert context.circuit_breaker_key == "service-a"
    print("✅ ContextBuilder.with_circuit_breaker worked")


@pytest.mark.unit
def test_context_builder_with_caching():
    """
    Test that ContextBuilder.with_caching sets cache key.
    """
    context = ContextBuilder().with_caching("query:123").build()

    assert context.cache_key == "query:123"
    print("✅ ContextBuilder.with_caching worked")


@pytest.mark.unit
def test_context_builder_with_correlation_id():
    """
    Test that ContextBuilder.with_correlation_id sets correlation ID.
    """
    correlation_id = uuid4()
    context = ContextBuilder().with_correlation_id(correlation_id).build()

    assert context.correlation_id == correlation_id
    print("✅ ContextBuilder.with_correlation_id worked")


@pytest.mark.unit
def test_context_builder_chains_methods():
    """
    Test that ContextBuilder methods can be chained fluently.
    """
    correlation_id = uuid4()
    context = (
        ContextBuilder()
        .with_user("user-123", roles=["admin"])
        .with_workspace("workspace-456")
        .with_transaction(requires_transaction=True)
        .with_rate_limiting("user-123")
        .with_circuit_breaker("service-a")
        .with_caching("cache-key")
        .with_correlation_id(correlation_id)
        .build()
    )

    assert context.user_id == "user-123"
    assert context.workspace_id == "workspace-456"
    assert context.requires_transaction is True
    assert context.rate_limit_key == "user-123"
    assert context.circuit_breaker_key == "service-a"
    assert context.cache_key == "cache-key"
    assert context.correlation_id == correlation_id
    print("✅ ContextBuilder chained methods")


# ============================================================================
# Domain Exception Tests
# ============================================================================


@pytest.mark.unit
def test_domain_exception_has_message():
    """
    Test that DomainException stores message.
    """
    exception = DomainException("Test error")

    assert exception.message == "Test error"
    assert str(exception) == "Test error"
    print("✅ DomainException has message")


@pytest.mark.unit
def test_not_found_exception():
    """
    Test that NotFoundException formats message correctly.
    """
    exception = NotFoundException("User", "user-123")

    assert exception.entity_name == "User"
    assert exception.identifier == "user-123"
    assert "User" in str(exception)
    assert "user-123" in str(exception)
    assert "not found" in str(exception)
    print("✅ NotFoundException formatted correctly")


@pytest.mark.unit
def test_duplicate_entity_exception():
    """
    Test that DuplicateEntityException formats message correctly.
    """
    exception = DuplicateEntityException("User", "john@example.com")

    assert exception.entity_name == "User"
    assert exception.identifier == "john@example.com"
    assert "User" in str(exception)
    assert "already exists" in str(exception)
    print("✅ DuplicateEntityException formatted correctly")


@pytest.mark.unit
def test_validation_exception():
    """
    Test that ValidationException stores field and message.
    """
    exception = ValidationException("email", "Invalid email format")

    assert exception.field == "email"
    assert exception.validation_message == "Invalid email format"
    assert "email" in str(exception)
    assert "Invalid email format" in str(exception)
    print("✅ ValidationException formatted correctly")


@pytest.mark.unit
def test_unauthorized_exception():
    """
    Test that UnauthorizedException formats message correctly.
    """
    exception = UnauthorizedException("delete user")

    assert exception.operation == "delete user"
    assert "Unauthorized" in str(exception)
    assert "delete user" in str(exception)
    print("✅ UnauthorizedException formatted correctly")


# ============================================================================
# Pipeline Exception Tests
# ============================================================================


@pytest.mark.unit
def test_pipeline_exception_has_attributes():
    """
    Test that PipelineException stores all attributes.
    """
    inner = ValueError("Inner error")
    exception = PipelineException("Test error", "TestCommand", inner)

    assert exception.message == "Test error"
    assert exception.request_type == "TestCommand"
    assert exception.inner_exception is inner
    print("✅ PipelineException has attributes")


@pytest.mark.unit
def test_handler_not_found_exception():
    """
    Test that HandlerNotFoundException formats message with type info.
    """

    class TestCommand(ICommand):
        pass

    exception = HandlerNotFoundException(TestCommand)

    assert exception.request_type == "TestCommand"
    assert exception.request_type_class is TestCommand
    assert "No handler registered" in str(exception)
    assert "TestCommand" in str(exception)
    print("✅ HandlerNotFoundException formatted correctly")


@pytest.mark.unit
def test_pipeline_execution_exception():
    """
    Test that PipelineExecutionException includes behavior type.
    """
    inner = ValueError("Failed")
    exception = PipelineExecutionException(
        "Something failed", "TestCommand", "ValidationBehavior", inner
    )

    assert exception.behavior_type == "ValidationBehavior"
    assert exception.request_type == "TestCommand"
    assert exception.inner_exception is inner
    assert "ValidationBehavior" in str(exception)
    assert "TestCommand" in str(exception)
    print("✅ PipelineExecutionException formatted correctly")


@pytest.mark.unit
def test_validation_pipeline_exception():
    """
    Test that ValidationPipelineException stores validation errors.
    """
    errors = ["Field 'name' is required", "Field 'age' must be positive"]
    exception = ValidationPipelineException("TestCommand", errors)

    assert exception.validation_errors == errors
    assert exception.behavior_type == "ValidationBehavior"
    assert "Validation failed" in str(exception)
    print("✅ ValidationPipelineException formatted correctly")


@pytest.mark.unit
def test_authorization_pipeline_exception_with_permission():
    """
    Test that AuthorizationPipelineException includes permission info.
    """
    exception = AuthorizationPipelineException("TestCommand", "user-123", "admin:write")

    assert exception.user_id == "user-123"
    assert exception.required_permission == "admin:write"
    assert "user-123" in str(exception)
    assert "admin:write" in str(exception)
    print("✅ AuthorizationPipelineException with permission formatted correctly")


@pytest.mark.unit
def test_authorization_pipeline_exception_without_permission():
    """
    Test that AuthorizationPipelineException handles missing permission.
    """
    exception = AuthorizationPipelineException("TestCommand")

    assert exception.user_id is None
    assert exception.required_permission is None
    assert "Authentication required" in str(exception)
    print("✅ AuthorizationPipelineException without permission formatted correctly")


@pytest.mark.unit
def test_transaction_pipeline_exception():
    """
    Test that TransactionPipelineException includes operation info.
    """
    inner = ValueError("DB error")
    exception = TransactionPipelineException("TestCommand", "commit", inner)

    assert exception.operation == "commit"
    assert exception.inner_exception is inner
    assert "commit" in str(exception)
    print("✅ TransactionPipelineException formatted correctly")


@pytest.mark.unit
def test_rate_limit_exceeded_exception():
    """
    Test that RateLimitExceededException includes rate info.
    """
    exception = RateLimitExceededException("user-123", 60)

    assert exception.rate_limit_key == "user-123"
    assert exception.requests_per_minute == 60
    assert "user-123" in str(exception)
    assert "60" in str(exception)
    print("✅ RateLimitExceededException formatted correctly")


@pytest.mark.unit
def test_circuit_breaker_open_exception():
    """
    Test that CircuitBreakerOpenException includes failure info.
    """
    exception = CircuitBreakerOpenException("service-a", 5, 3)

    assert exception.circuit_key == "service-a"
    assert exception.failure_count == 5
    assert exception.failure_threshold == 3
    assert "service-a" in str(exception)
    assert "5/3" in str(exception)
    print("✅ CircuitBreakerOpenException formatted correctly")


@pytest.mark.unit
def test_handler_registration_exception():
    """
    Test that HandlerRegistrationException includes handler and request types.
    """

    class TestHandler:
        pass

    class TestCommand(ICommand):
        pass

    exception = HandlerRegistrationException(TestHandler, TestCommand, "Already registered")

    assert exception.handler_type is TestHandler
    assert exception.request_type_class is TestCommand
    assert exception.reason == "Already registered"
    assert "TestHandler" in str(exception)
    assert "TestCommand" in str(exception)
    assert "Already registered" in str(exception)
    print("✅ HandlerRegistrationException formatted correctly")


@pytest.mark.unit
def test_all_exceptions_inherit_from_base():
    """
    Test that all custom exceptions inherit from proper base classes.
    """
    # Domain exceptions
    assert issubclass(NotFoundException, DomainException)
    assert issubclass(DuplicateEntityException, DomainException)
    assert issubclass(ValidationException, DomainException)
    assert issubclass(UnauthorizedException, DomainException)

    # Pipeline exceptions
    assert issubclass(HandlerNotFoundException, PipelineException)
    assert issubclass(PipelineExecutionException, PipelineException)
    assert issubclass(ValidationPipelineException, PipelineExecutionException)
    assert issubclass(AuthorizationPipelineException, PipelineExecutionException)
    assert issubclass(TransactionPipelineException, PipelineExecutionException)

    print("✅ All exceptions inherit from proper base classes")
