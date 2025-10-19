"""
Unit tests for Pipeline Behaviors
"""

import asyncio
import logging
import time
from typing import Any

import pytest
from pydantic import BaseModel, field_validator

from libs.buildingblocks.behaviors.pipeline_behaviors import (
    AuthorizationBehavior,
    CachingBehavior,
    CircuitBreakerBehavior,
    IPipelineBehavior,
    LoggingBehavior,
    RateLimitingBehavior,
    TransactionBehavior,
    ValidationBehavior,
)
from libs.buildingblocks.cqrs.interfaces import ICommand, IQuery
from libs.buildingblocks.exceptions.pipeline_exceptions import (
    AuthorizationPipelineException,
    CircuitBreakerOpenException,
    RateLimitExceededException,
    ValidationPipelineException,
)


# Test Models
class ValidPydanticCommand(BaseModel, ICommand):
    name: str
    age: int

    @field_validator("age")
    @classmethod
    def validate_age(cls, v):
        if v < 0:
            raise ValueError("Age must be positive")
        return v


class InvalidPydanticCommand(BaseModel, ICommand):
    name: str
    age: int

    @field_validator("age")
    @classmethod
    def validate_age(cls, v):
        if v < 18:
            raise ValueError("Age must be 18 or older")
        return v


class CustomValidationCommand(ICommand):
    def __init__(self, value: str):
        self.value = value

    def validate(self):
        if not self.value:
            raise ValueError("Value cannot be empty")


class AsyncValidationCommand(ICommand):
    def __init__(self, value: str):
        self.value = value

    async def validate(self):
        await asyncio.sleep(0.01)  # Simulate async validation
        if not self.value:
            raise ValueError("Value cannot be empty")


class CommandWithCorrelationId(ICommand):
    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id


class CommandWithUserContext(ICommand):
    def __init__(self, user_context=None):
        self.user_context = user_context


class CommandWithAuthorize(ICommand):
    def __init__(self, should_authorize: bool):
        self.should_authorize = should_authorize

    async def authorize(self, user_context):
        return self.should_authorize


class CacheableQuery(IQuery[str]):
    def __init__(self, cache_key: str):
        self.cache_key = cache_key


class RateLimitedCommand(ICommand):
    def __init__(self, rate_limit_key: str):
        self.rate_limit_key = rate_limit_key


class CircuitBreakerCommand(ICommand):
    def __init__(self, circuit_breaker_key: str):
        self.circuit_breaker_key = circuit_breaker_key


# Helper functions
async def success_handler():
    """Handler that succeeds"""
    return "success"


async def failing_handler():
    """Handler that fails"""
    raise ValueError("Handler failed")


# ============================================================================
# ValidationBehavior Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validation_behavior_passes_valid_pydantic_model():
    """
    Test that ValidationBehavior passes valid Pydantic models.
    """
    behavior = ValidationBehavior()
    command = ValidPydanticCommand(name="John", age=25)

    result = await behavior.handle(command, success_handler)

    assert result == "success"
    print("✅ ValidationBehavior passed valid Pydantic model")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validation_behavior_rejects_invalid_pydantic_model():
    """
    Test that ValidationBehavior raises ValidationPipelineException for invalid models.
    """
    behavior = ValidationBehavior()

    # Pydantic validation happens at instantiation, so we catch it differently
    # Create a valid instance first, then modify it to invalid state
    command = InvalidPydanticCommand(name="John", age=20)
    
    # Manually set invalid age to bypass constructor validation
    command.__dict__["age"] = 15

    with pytest.raises(ValidationPipelineException) as exc_info:
        await behavior.handle(command, success_handler)

    assert "Age must be 18 or older" in str(exc_info.value)
    print("✅ ValidationBehavior rejected invalid Pydantic model")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validation_behavior_calls_custom_validate():
    """
    Test that ValidationBehavior calls custom validate() method.
    """
    behavior = ValidationBehavior()
    command = CustomValidationCommand(value="valid")

    result = await behavior.handle(command, success_handler)

    assert result == "success"
    print("✅ ValidationBehavior called custom validate()")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validation_behavior_rejects_custom_validation_failure():
    """
    Test that ValidationBehavior raises exception for custom validation failure.
    """
    behavior = ValidationBehavior()
    command = CustomValidationCommand(value="")

    with pytest.raises(ValueError) as exc_info:
        await behavior.handle(command, success_handler)

    assert "Value cannot be empty" in str(exc_info.value)
    print("✅ ValidationBehavior rejected custom validation failure")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validation_behavior_supports_async_validate():
    """
    Test that ValidationBehavior supports async validate() methods.
    """
    behavior = ValidationBehavior()
    command = AsyncValidationCommand(value="valid")

    result = await behavior.handle(command, success_handler)

    assert result == "success"
    print("✅ ValidationBehavior supported async validate()")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validation_behavior_skips_non_validatable():
    """
    Test that ValidationBehavior skips objects without validation.
    """
    behavior = ValidationBehavior()

    class SimpleCommand(ICommand):
        pass

    command = SimpleCommand()
    result = await behavior.handle(command, success_handler)

    assert result == "success"
    print("✅ ValidationBehavior skipped non-validatable object")


# ============================================================================
# LoggingBehavior Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_logging_behavior_logs_request_execution(caplog):
    """
    Test that LoggingBehavior logs request execution.
    """
    with caplog.at_level(logging.INFO):
        behavior = LoggingBehavior(enable_request_logging=True)
        command = CommandWithCorrelationId(correlation_id="test-123")

        await behavior.handle(command, success_handler)

        assert "Handling CommandWithCorrelationId" in caplog.text
        assert "test-123" in caplog.text
        assert "SUCCESS" in caplog.text
    print("✅ LoggingBehavior logged request execution")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_logging_behavior_warns_on_slow_requests(caplog):
    """
    Test that LoggingBehavior warns when requests exceed threshold.
    """

    async def slow_handler():
        await asyncio.sleep(0.1)
        return "slow"

    with caplog.at_level(logging.WARNING):
        behavior = LoggingBehavior(slow_threshold=0.05)
        command = CommandWithCorrelationId(correlation_id="slow-request")

        await behavior.handle(command, slow_handler)

        assert "PERFORMANCE" in caplog.text
        assert "threshold" in caplog.text
    print("✅ LoggingBehavior warned on slow request")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_logging_behavior_logs_errors(caplog):
    """
    Test that LoggingBehavior logs errors with details.
    """
    with caplog.at_level(logging.ERROR):
        behavior = LoggingBehavior()
        command = CommandWithCorrelationId(correlation_id="error-request")

        with pytest.raises(ValueError):
            await behavior.handle(command, failing_handler)

        assert "ERROR" in caplog.text
        assert "failed" in caplog.text
    print("✅ LoggingBehavior logged error")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_logging_behavior_handles_missing_correlation_id(caplog):
    """
    Test that LoggingBehavior handles missing correlation_id gracefully.
    """

    class SimpleCommand(ICommand):
        pass

    with caplog.at_level(logging.INFO):
        behavior = LoggingBehavior()
        command = SimpleCommand()

        await behavior.handle(command, success_handler)

        assert "unknown" in caplog.text  # Default correlation ID
    print("✅ LoggingBehavior handled missing correlation_id")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_logging_behavior_can_disable_request_logging(caplog):
    """
    Test that LoggingBehavior can disable request logging.
    """
    with caplog.at_level(logging.INFO):
        behavior = LoggingBehavior(enable_request_logging=False)
        command = CommandWithCorrelationId(correlation_id="test")

        await behavior.handle(command, success_handler)

        # Should still log success but not START
        assert "START" not in caplog.text
        assert "SUCCESS" in caplog.text
    print("✅ LoggingBehavior disabled request logging")


# ============================================================================
# AuthorizationBehavior Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authorization_behavior_requires_user_context():
    """
    Test that AuthorizationBehavior requires user_context when authentication required.
    """
    behavior = AuthorizationBehavior(require_authentication=True)
    command = CommandWithUserContext(user_context=None)

    with pytest.raises(AuthorizationPipelineException):
        await behavior.handle(command, success_handler)

    print("✅ AuthorizationBehavior required user_context")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authorization_behavior_passes_with_user_context():
    """
    Test that AuthorizationBehavior passes when user_context provided.
    """

    class MockUser:
        user_id = "user-123"

    behavior = AuthorizationBehavior(require_authentication=True)
    command = CommandWithUserContext(user_context=MockUser())

    result = await behavior.handle(command, success_handler)

    assert result == "success"
    print("✅ AuthorizationBehavior passed with user_context")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authorization_behavior_calls_custom_authorize():
    """
    Test that AuthorizationBehavior calls custom authorize() method.
    """

    class MockUser:
        user_id = "user-123"

    behavior = AuthorizationBehavior(require_authentication=False)
    command = CommandWithAuthorize(should_authorize=True)
    command.user_context = MockUser()

    result = await behavior.handle(command, success_handler)

    assert result == "success"
    print("✅ AuthorizationBehavior called custom authorize()")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authorization_behavior_rejects_unauthorized():
    """
    Test that AuthorizationBehavior rejects unauthorized requests.
    """

    class MockUser:
        user_id = "user-123"

    behavior = AuthorizationBehavior(require_authentication=False)
    command = CommandWithAuthorize(should_authorize=False)
    command.user_context = MockUser()

    with pytest.raises(AuthorizationPipelineException) as exc_info:
        await behavior.handle(command, success_handler)

    assert exc_info.value.user_id == "user-123"
    print("✅ AuthorizationBehavior rejected unauthorized request")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authorization_behavior_skip_when_not_required():
    """
    Test that AuthorizationBehavior skips check when not required.
    """
    behavior = AuthorizationBehavior(require_authentication=False)
    command = CommandWithUserContext(user_context=None)

    result = await behavior.handle(command, success_handler)

    assert result == "success"
    print("✅ AuthorizationBehavior skipped when not required")


# ============================================================================
# CachingBehavior Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_caching_behavior_caches_results():
    """
    Test that CachingBehavior caches query results.
    """
    behavior = CachingBehavior(cache_ttl=60)
    call_count = 0

    async def counted_handler():
        nonlocal call_count
        call_count += 1
        return f"result_{call_count}"

    query = CacheableQuery(cache_key="test-key")

    # First call
    result1 = await behavior.handle(query, counted_handler)
    assert result1 == "result_1"
    assert call_count == 1

    # Second call should use cache
    result2 = await behavior.handle(query, counted_handler)
    assert result2 == "result_1"  # Cached result
    assert call_count == 1  # Handler not called again

    print("✅ CachingBehavior cached results")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_caching_behavior_expires_after_ttl():
    """
    Test that CachingBehavior expires cache after TTL.
    """
    behavior = CachingBehavior(cache_ttl=0.1)  # 100ms TTL
    call_count = 0

    async def counted_handler():
        nonlocal call_count
        call_count += 1
        return f"result_{call_count}"

    query = CacheableQuery(cache_key="test-key")

    # First call
    result1 = await behavior.handle(query, counted_handler)
    assert result1 == "result_1"

    # Wait for TTL to expire
    await asyncio.sleep(0.15)

    # Second call should execute handler
    result2 = await behavior.handle(query, counted_handler)
    assert result2 == "result_2"
    assert call_count == 2

    print("✅ CachingBehavior expired cache after TTL")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_caching_behavior_skips_non_cacheable():
    """
    Test that CachingBehavior skips requests without cache_key.
    """
    behavior = CachingBehavior()

    class NonCacheableCommand(ICommand):
        pass

    call_count = 0

    async def counted_handler():
        nonlocal call_count
        call_count += 1
        return "result"

    command = NonCacheableCommand()

    await behavior.handle(command, counted_handler)
    await behavior.handle(command, counted_handler)

    assert call_count == 2  # Handler called both times
    print("✅ CachingBehavior skipped non-cacheable request")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_caching_behavior_can_be_disabled():
    """
    Test that CachingBehavior can be disabled.
    """
    behavior = CachingBehavior(enable_caching=False)
    call_count = 0

    async def counted_handler():
        nonlocal call_count
        call_count += 1
        return f"result_{call_count}"

    query = CacheableQuery(cache_key="test-key")

    await behavior.handle(query, counted_handler)
    await behavior.handle(query, counted_handler)

    assert call_count == 2  # Handler called both times (caching disabled)
    print("✅ CachingBehavior can be disabled")


# ============================================================================
# RateLimitingBehavior Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiting_behavior_allows_within_limit():
    """
    Test that RateLimitingBehavior allows requests within limit.
    """
    behavior = RateLimitingBehavior(requests_per_minute=5)
    command = RateLimitedCommand(rate_limit_key="user-123")

    # Should allow 5 requests
    for i in range(5):
        result = await behavior.handle(command, success_handler)
        assert result == "success"

    print("✅ RateLimitingBehavior allowed requests within limit")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiting_behavior_rejects_over_limit():
    """
    Test that RateLimitingBehavior rejects requests over limit.
    """
    behavior = RateLimitingBehavior(requests_per_minute=3)
    command = RateLimitedCommand(rate_limit_key="user-123")

    # Allow 3 requests
    for i in range(3):
        await behavior.handle(command, success_handler)

    # 4th request should be rejected
    with pytest.raises(RateLimitExceededException) as exc_info:
        await behavior.handle(command, success_handler)

    assert exc_info.value.rate_limit_key == "user-123"
    print("✅ RateLimitingBehavior rejected request over limit")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiting_behavior_per_key():
    """
    Test that RateLimitingBehavior tracks limits per key independently.
    """
    behavior = RateLimitingBehavior(requests_per_minute=2)

    command1 = RateLimitedCommand(rate_limit_key="user-1")
    command2 = RateLimitedCommand(rate_limit_key="user-2")

    # Both users can make 2 requests
    await behavior.handle(command1, success_handler)
    await behavior.handle(command1, success_handler)
    await behavior.handle(command2, success_handler)
    await behavior.handle(command2, success_handler)

    # Both should be rate limited now
    with pytest.raises(RateLimitExceededException):
        await behavior.handle(command1, success_handler)

    with pytest.raises(RateLimitExceededException):
        await behavior.handle(command2, success_handler)

    print("✅ RateLimitingBehavior tracked limits per key")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiting_behavior_skips_without_key():
    """
    Test that RateLimitingBehavior skips requests without rate_limit_key.
    """
    behavior = RateLimitingBehavior(requests_per_minute=1)

    class NonRateLimitedCommand(ICommand):
        pass

    command = NonRateLimitedCommand()

    # Should allow unlimited requests
    for i in range(5):
        result = await behavior.handle(command, success_handler)
        assert result == "success"

    print("✅ RateLimitingBehavior skipped request without key")


# ============================================================================
# CircuitBreakerBehavior Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_circuit_breaker_behavior_opens_after_failures():
    """
    Test that CircuitBreakerBehavior opens circuit after failure threshold.
    """
    behavior = CircuitBreakerBehavior(failure_threshold=3, recovery_timeout=60)
    command = CircuitBreakerCommand(circuit_breaker_key="service-a")

    # Cause 3 failures
    for i in range(3):
        with pytest.raises(ValueError):
            await behavior.handle(command, failing_handler)

    # Circuit should now be open
    with pytest.raises(CircuitBreakerOpenException) as exc_info:
        await behavior.handle(command, success_handler)

    assert exc_info.value.circuit_key == "service-a"
    print("✅ CircuitBreakerBehavior opened after failures")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_circuit_breaker_behavior_resets_on_success():
    """
    Test that CircuitBreakerBehavior resets failure count on success.
    """
    behavior = CircuitBreakerBehavior(failure_threshold=3)
    command = CircuitBreakerCommand(circuit_breaker_key="service-a")

    # Cause 2 failures
    for i in range(2):
        with pytest.raises(ValueError):
            await behavior.handle(command, failing_handler)

    # Success should reset
    result = await behavior.handle(command, success_handler)
    assert result == "success"

    # Should allow more requests
    result = await behavior.handle(command, success_handler)
    assert result == "success"

    print("✅ CircuitBreakerBehavior reset on success")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_circuit_breaker_behavior_per_key():
    """
    Test that CircuitBreakerBehavior tracks circuits per key independently.
    """
    behavior = CircuitBreakerBehavior(failure_threshold=2)

    command_a = CircuitBreakerCommand(circuit_breaker_key="service-a")
    command_b = CircuitBreakerCommand(circuit_breaker_key="service-b")

    # Fail service A twice
    for i in range(2):
        with pytest.raises(ValueError):
            await behavior.handle(command_a, failing_handler)

    # Service A circuit open
    with pytest.raises(CircuitBreakerOpenException):
        await behavior.handle(command_a, success_handler)

    # Service B still works
    result = await behavior.handle(command_b, success_handler)
    assert result == "success"

    print("✅ CircuitBreakerBehavior tracked circuits per key")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_circuit_breaker_behavior_skips_without_key():
    """
    Test that CircuitBreakerBehavior skips requests without circuit_breaker_key.
    """
    behavior = CircuitBreakerBehavior(failure_threshold=1)

    class NonCircuitCommand(ICommand):
        pass

    command = NonCircuitCommand()

    # Should always execute even with failures
    for i in range(5):
        with pytest.raises(ValueError):
            await behavior.handle(command, failing_handler)

    print("✅ CircuitBreakerBehavior skipped request without key")
