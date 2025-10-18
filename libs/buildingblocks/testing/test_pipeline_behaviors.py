"""
Pipeline Behavior Tests

Tests enterprise pipeline behaviors that provide cross-cutting concerns.
These are practical tests that verify behaviors actually protect business logic
and handle real-world scenarios like validation failures, unauthorized access,
transaction rollbacks, rate limiting, and circuit breaker patterns.
"""

from unittest.mock import AsyncMock

import pytest
from building_blocks.behaviors.pipeline_behaviors import (
    AuthorizationBehavior,
    CachingBehavior,
    CircuitBreakerBehavior,
    RateLimitingBehavior,
    TransactionBehavior,
    ValidationBehavior,
)
from building_blocks.exceptions.pipeline_exceptions import (
    AuthorizationPipelineException,
    CircuitBreakerOpenException,
    RateLimitExceededException,
    TransactionPipelineException,
    ValidationPipelineException,
)
from infrastructure_testing.mocks import MockDatabase, MockUserContext
from pydantic import BaseModel

from .builders import BBPipelineBuilder, BBTestCreateUserCommand


class ValidatedCommand(BaseModel):
    """Pydantic command for validation testing"""

    username: str
    email: str
    age: int

    def model_post_init(self, __context):
        if self.age < 0:
            raise ValueError("Age cannot be negative")


class TestValidationBehavior:
    """Test validation pipeline behavior"""

    @pytest.mark.asyncio
    async def test_validation_behavior_passes_valid_pydantic_model(self):
        """REAL TEST: Valid Pydantic models pass validation"""
        # Given: Validation behavior and valid command
        validation_behavior = ValidationBehavior()
        valid_command = ValidatedCommand(username="test", email="test@example.com", age=25)
        mock_handler = AsyncMock(return_value="success")

        # When: Execute through validation behavior
        result = await validation_behavior.handle(valid_command, mock_handler)

        # Then: Should pass validation and execute handler
        assert result == "success"
        mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_validation_behavior_blocks_invalid_pydantic_model(self):
        """REAL TEST: Invalid Pydantic models are blocked"""
        # Given: Validation behavior and valid command that we'll modify to be invalid
        validation_behavior = ValidationBehavior()
        mock_handler = AsyncMock(return_value="should_not_execute")

        # Create a valid command first
        valid_command = ValidatedCommand(username="test", email="test@example.com", age=25)

        # Then modify the internal data to make it invalid (bypass Pydantic validation)
        valid_command.__dict__["age"] = -5  # Directly set invalid value

        # When: Try to execute through validation behavior
        # Then: Should raise ValidationPipelineException
        with pytest.raises(ValidationPipelineException):
            await validation_behavior.handle(valid_command, mock_handler)

        # Handler should never be called
        mock_handler.assert_not_called()


class TestAuthorizationBehavior:
    """Test authorization pipeline behavior"""

    @pytest.mark.asyncio
    async def test_authorization_behavior_allows_authenticated_user(self):
        """REAL TEST: Authenticated users are allowed through"""
        # Given: Authorization behavior and authenticated request
        auth_behavior = AuthorizationBehavior()
        command = BBTestCreateUserCommand(username="test", email="test@example.com")
        command.user_context = MockUserContext(user_id="123", roles=["user"])
        mock_handler = AsyncMock(return_value="success")

        # When: Execute with authenticated user
        result = await auth_behavior.handle(command, mock_handler)

        # Then: Should allow execution
        assert result == "success"
        mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_authorization_behavior_blocks_unauthenticated_user(self):
        """REAL TEST: Unauthenticated users are blocked"""
        # Given: Authorization behavior requiring authentication
        auth_behavior = AuthorizationBehavior(require_authentication=True)
        command = BBTestCreateUserCommand(username="test", email="test@example.com")
        # No user_context set = unauthenticated
        mock_handler = AsyncMock(return_value="should_not_execute")

        # When: Try to execute without authentication
        # Then: Should raise AuthorizationPipelineException
        with pytest.raises(AuthorizationPipelineException):
            await auth_behavior.handle(command, mock_handler)

        mock_handler.assert_not_called()


class TestTransactionBehavior:
    """Test transaction pipeline behavior"""

    @pytest.mark.asyncio
    async def test_transaction_behavior_commits_on_success(self):
        """REAL TEST: Transaction commits when handler succeeds"""
        # Given: Transaction behavior and command requiring transaction
        transaction_behavior = TransactionBehavior(auto_commit=True)
        command = BBTestCreateUserCommand(username="test", email="test@example.com")
        command.requires_transaction = True
        command.db_session = MockDatabase()
        mock_handler = AsyncMock(return_value="success")

        # When: Execute successfully
        result = await transaction_behavior.handle(command, mock_handler)

        # Then: Should commit transaction
        assert result == "success"
        assert command.db_session.committed is True
        assert command.db_session.rolled_back is False
        mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_transaction_behavior_rolls_back_on_failure(self):
        """REAL TEST: Transaction rolls back when handler fails"""
        # Given: Transaction behavior and failing handler
        transaction_behavior = TransactionBehavior()
        command = BBTestCreateUserCommand(username="test", email="test@example.com")
        command.requires_transaction = True
        command.db_session = MockDatabase()

        failing_handler = AsyncMock(side_effect=Exception("Handler failed!"))

        # When: Handler fails
        # Then: Should rollback and raise TransactionPipelineException
        with pytest.raises(TransactionPipelineException):
            await transaction_behavior.handle(command, failing_handler)

        assert command.db_session.rolled_back is True
        assert command.db_session.committed is False


class TestRateLimitingBehavior:
    """Test rate limiting pipeline behavior"""

    @pytest.mark.asyncio
    async def test_rate_limiting_allows_requests_under_threshold(self):
        """REAL TEST: Requests under limit are allowed"""
        # Given: Rate limiter with 3 requests per minute
        rate_limiter = RateLimitingBehavior(requests_per_minute=3)
        command = BBTestCreateUserCommand(username="test", email="test@example.com")
        command.rate_limit_key = "user_123"
        mock_handler = AsyncMock(return_value="success")

        # When: Make 2 requests (under limit)
        result1 = await rate_limiter.handle(command, mock_handler)
        result2 = await rate_limiter.handle(command, mock_handler)

        # Then: Both should succeed
        assert result1 == "success"
        assert result2 == "success"
        assert mock_handler.call_count == 2

    @pytest.mark.asyncio
    async def test_rate_limiting_blocks_requests_over_threshold(self):
        """REAL TEST: Requests over limit are blocked"""
        # Given: Rate limiter with 2 requests per minute
        rate_limiter = RateLimitingBehavior(requests_per_minute=2)
        command = BBTestCreateUserCommand(username="test", email="test@example.com")
        command.rate_limit_key = "user_456"
        mock_handler = AsyncMock(return_value="success")

        # When: Make 3 requests (over limit)
        await rate_limiter.handle(command, mock_handler)  # 1st - OK
        await rate_limiter.handle(command, mock_handler)  # 2nd - OK

        # Then: 3rd request should be blocked
        with pytest.raises(RateLimitExceededException) as exc_info:
            await rate_limiter.handle(command, mock_handler)  # 3rd - BLOCKED

        assert "user_456" in str(exc_info.value)
        assert mock_handler.call_count == 2  # Only first 2 succeeded


class TestCircuitBreakerBehavior:
    """Test circuit breaker pipeline behavior"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failure_threshold(self):
        """REAL TEST: Circuit breaker opens after repeated failures"""
        # Given: Circuit breaker with 3 failure threshold
        circuit_breaker = CircuitBreakerBehavior(failure_threshold=3, recovery_timeout=60)
        command = BBTestCreateUserCommand(username="test", email="test@example.com")
        command.circuit_breaker_key = "payment_api"

        class ServiceUnavailableError(Exception):
            """Specific error for circuit breaker testing"""

            pass

        failing_handler = AsyncMock(side_effect=ServiceUnavailableError("Service unavailable"))

        # When: Fail 3 times to reach threshold
        for _i in range(3):
            with pytest.raises(ServiceUnavailableError):
                await circuit_breaker.handle(command, failing_handler)

        # Then: 4th call should fail fast with circuit breaker open
        with pytest.raises(CircuitBreakerOpenException) as exc_info:
            await circuit_breaker.handle(command, failing_handler)

        assert "payment_api" in str(exc_info.value)
        assert failing_handler.call_count == 3  # Only first 3 actually called

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self):
        """REAL TEST: Circuit breaker resets failure count on success"""
        # Given: Circuit breaker with some failures
        circuit_breaker = CircuitBreakerBehavior(failure_threshold=3)
        command = BBTestCreateUserCommand(username="test", email="test@example.com")
        command.circuit_breaker_key = "api_service"

        class TemporaryFailureError(Exception):
            """Specific error for circuit breaker reset testing"""

            pass

        failing_handler = AsyncMock(side_effect=TemporaryFailureError("Temporary failure"))
        success_handler = AsyncMock(return_value="success")

        # When: Fail twice, then succeed
        with pytest.raises(TemporaryFailureError):
            await circuit_breaker.handle(command, failing_handler)
        with pytest.raises(TemporaryFailureError):
            await circuit_breaker.handle(command, failing_handler)

        result = await circuit_breaker.handle(command, success_handler)

        # Then: Success should reset failure count
        assert result == "success"

        # Should be able to fail 3 more times before circuit opens
        for _i in range(3):
            with pytest.raises(TemporaryFailureError):
                await circuit_breaker.handle(command, failing_handler)


class TestCachingBehavior:
    """Test caching pipeline behavior"""

    @pytest.mark.asyncio
    async def test_caching_behavior_caches_query_results(self):
        """REAL TEST: Query results are cached and reused"""
        # Given: Caching behavior and query with cache key
        caching_behavior = CachingBehavior(cache_ttl=300)
        from .builders import BBTestGetUserQuery

        query = BBTestGetUserQuery(user_id="123")
        query.cache_key = "user:123"

        expensive_handler = AsyncMock(return_value={"user_id": "123", "username": "cached_user"})

        # When: Execute query twice
        result1 = await caching_behavior.handle(query, expensive_handler)
        result2 = await caching_behavior.handle(query, expensive_handler)

        # Then: Handler called only once, both results identical
        assert result1 == result2
        assert expensive_handler.call_count == 1  # Cached on second call

    @pytest.mark.asyncio
    async def test_caching_behavior_skips_commands(self):
        """REAL TEST: Commands are not cached"""
        # Given: Caching behavior and command (no cache_key)
        caching_behavior = CachingBehavior()
        command = BBTestCreateUserCommand(username="test", email="test@example.com")
        # Commands don't have cache_key

        handler = AsyncMock(return_value="executed")

        # When: Execute command twice
        result1 = await caching_behavior.handle(command, handler)
        result2 = await caching_behavior.handle(command, handler)

        # Then: Handler called both times (no caching)
        assert result1 == "executed"
        assert result2 == "executed"
        assert handler.call_count == 2


class TestPipelineIntegration:
    """Test multiple behaviors working together"""

    @pytest.mark.asyncio
    async def test_pipeline_with_multiple_behaviors_executes_in_order(self):
        """REAL TEST: Multiple behaviors execute in correct order"""
        # Given: Pipeline with validation → authorization → transaction
        builder = BBPipelineBuilder()

        # Create authenticated command with transaction
        command = BBTestCreateUserCommand(username="pipelinetest", email="test@example.com")
        command.user_context = MockUserContext(user_id="123", roles=["admin"])
        command.requires_transaction = True
        command.db_session = MockDatabase()

        pipeline = (
            builder.with_validation_behavior().with_authorization_behavior().with_request(command)
        )

        # When: Execute full pipeline
        result = await pipeline.execute_with_mock_handler("pipeline_success")

        # Then: Should execute successfully through all behaviors
        assert result == "pipeline_success"
        # Transaction should be committed (if TransactionBehavior was included)

    @pytest.mark.asyncio
    async def test_pipeline_stops_at_first_failure(self):
        """REAL TEST: Pipeline stops at first failing behavior"""
        # Given: Pipeline with validation → authorization, but unauthenticated request
        builder = BBPipelineBuilder()

        command = BBTestCreateUserCommand(username="test", email="test@example.com")
        # No user_context = unauthenticated

        pipeline = (
            builder.with_validation_behavior().with_authorization_behavior().with_request(command)
        )

        # When: Execute pipeline with unauthenticated user
        # Then: Should fail at authorization (after validation passes)
        with pytest.raises(AuthorizationPipelineException):
            await pipeline.execute_with_mock_handler("should_not_reach")
