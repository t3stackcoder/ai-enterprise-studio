"""
Circuit Breaker Tests

Tests circuit breaker pattern for preventing cascading failures.
Validates circuit states: Closed → Open → Half-Open → Closed recovery.
"""

import os
import sys
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable
from uuid import uuid4

import pytest
from buildingblocks.cqrs import ICommand, ICommandHandler, IQuery, IQueryHandler


# ============================================================================
# Circuit Breaker Implementation
# ============================================================================


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Too many failures, reject immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Simple circuit breaker implementation"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 5.0,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function through circuit breaker"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                print(f"⚡ Circuit HALF-OPEN, testing recovery...")
            else:
                raise ConnectionError(
                    f"Circuit breaker OPEN (failed {self.failure_count} times)"
                )

        try:
            # Handle both sync and async functions
            import asyncio
            import inspect
            if inspect.iscoroutinefunction(func) or asyncio.iscoroutine(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time passed to try recovery"""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.success_count = 0
                print(f"✅ Circuit CLOSED, service recovered!")

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.success_count = 0

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            print(
                f"🔴 Circuit OPEN after {self.failure_count} failures (will retry in {self.recovery_timeout}s)"
            )


# ============================================================================
# Commands & Queries
# ============================================================================


@dataclass
class UnreliableServiceCommand(ICommand):
    """Command that may fail"""

    data: str
    should_fail: bool = False


@dataclass
class ServiceHealthQuery(IQuery[bool]):
    """Query service health"""

    service_name: str


# ============================================================================
# Handlers
# ============================================================================


class UnreliableServiceHandler(ICommandHandler):
    """Handler that simulates unreliable service"""

    def __init__(self):
        self.call_count = 0
        self.success_count = 0

    async def handle(self, command: UnreliableServiceCommand) -> None:
        self.call_count += 1
        if command.should_fail:
            raise ConnectionError(f"Service unavailable (call #{self.call_count})")
        self.success_count += 1


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_circuit_opens_after_failures():
    """
    Test that circuit breaker opens after failure threshold.
    
    Scenario: 5 failures → Circuit opens → Subsequent calls fail immediately.
    """
    handler = UnreliableServiceHandler()
    circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=2.0)

    # Cause 5 failures to open circuit
    for i in range(5):
        command = UnreliableServiceCommand(data=f"attempt_{i}", should_fail=True)
        with pytest.raises(ConnectionError):
            await circuit.call(handler.handle, command)

    assert circuit.state == CircuitState.OPEN
    assert handler.call_count == 5

    # Next call should fail immediately without calling handler
    command = UnreliableServiceCommand(data="blocked", should_fail=False)
    with pytest.raises(ConnectionError) as exc_info:
        await circuit.call(handler.handle, command)

    assert "Circuit breaker OPEN" in str(exc_info.value)
    assert handler.call_count == 5  # Handler NOT called
    print(f"✅ Circuit opened after {circuit.failure_threshold} failures")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_circuit_recovery_after_timeout():
    """
    Test that circuit moves to half-open after recovery timeout.
    
    Scenario: Circuit open → Wait timeout → Half-open → Success → Closed.
    """
    handler = UnreliableServiceHandler()
    circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=0.5, success_threshold=2)

    # Open the circuit
    for i in range(3):
        command = UnreliableServiceCommand(data=f"fail_{i}", should_fail=True)
        with pytest.raises(ConnectionError):
            await circuit.call(handler.handle, command)

    assert circuit.state == CircuitState.OPEN
    print(f"🔴 Circuit opened")

    # Wait for recovery timeout
    time.sleep(0.6)

    # First call after timeout should move to half-open
    command = UnreliableServiceCommand(data="recovery_test", should_fail=False)
    await circuit.call(handler.handle, command)
    assert circuit.state == CircuitState.HALF_OPEN
    print(f"⚡ Circuit half-open, testing recovery")

    # Second success should close circuit
    command = UnreliableServiceCommand(data="recovery_confirm", should_fail=False)
    await circuit.call(handler.handle, command)
    assert circuit.state == CircuitState.CLOSED
    print(f"✅ Circuit closed, service recovered")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_circuit_reopens_on_half_open_failure():
    """
    Test that circuit reopens if half-open test fails.
    
    Scenario: Open → Half-open → Fail → Back to Open.
    """
    handler = UnreliableServiceHandler()
    circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=0.3)

    # Open circuit
    for i in range(3):
        with pytest.raises(ConnectionError):
            await circuit.call(
                handler.handle, UnreliableServiceCommand(data=f"fail_{i}", should_fail=True)
            )

    assert circuit.state == CircuitState.OPEN

    # Wait and attempt recovery
    time.sleep(0.4)

    # First call moves to half-open, but fails
    with pytest.raises(ConnectionError):
        await circuit.call(handler.handle, UnreliableServiceCommand(data="fail_again", should_fail=True))

    # Circuit should reopen
    assert circuit.state == CircuitState.OPEN
    assert circuit.failure_count >= circuit.failure_threshold
    print(f"✅ Circuit reopened after half-open failure")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_circuit_prevents_cascading_failures(minio_clean):
    """
    Test circuit breaker prevents cascade when MinIO is slow/failing.
    
    Simulates service degradation scenario.
    """
    call_times = []
    circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

    def failing_upload(bucket, object_name, data, length):
        """Simulate failing MinIO upload"""
        call_times.append(time.time())
        raise ConnectionError("MinIO connection timeout")

    # Cause failures to open circuit
    for i in range(3):
        with pytest.raises(ConnectionError):
            await circuit.call(failing_upload, "test-bucket", f"obj_{i}", b"data", 4)

    assert circuit.state == CircuitState.OPEN

    # Next 10 calls should fail fast without calling function
    start = time.time()
    for i in range(10):
        with pytest.raises(ConnectionError) as exc_info:
            await circuit.call(failing_upload, "test-bucket", f"blocked_{i}", b"data", 4)
        assert "Circuit breaker OPEN" in str(exc_info.value)

    elapsed = time.time() - start

    # Should fail instantly (< 100ms total for 10 calls)
    assert elapsed < 0.1
    assert len(call_times) == 3  # Only first 3 calls actually executed

    print(f"✅ Circuit breaker prevented 10 cascading failures in {elapsed*1000:.0f}ms")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_circuit_with_redis_operations(redis_clean):
    """
    Test circuit breaker with actual Redis operations.
    
    Simulates Redis going down and recovering.
    """
    circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=0.5, success_threshold=1)

    def redis_get_with_failure(key: str, should_fail: bool):
        if should_fail:
            raise ConnectionError("Redis connection refused")
        return redis_clean.get(key)

    def redis_set_with_failure(key: str, value: str, should_fail: bool):
        if should_fail:
            raise ConnectionError("Redis connection refused")
        redis_clean.set(key, value)

    # Simulate Redis failures
    for i in range(3):
        with pytest.raises(ConnectionError):
            await circuit.call(redis_get_with_failure, f"key_{i}", should_fail=True)

    assert circuit.state == CircuitState.OPEN
    print(f"🔴 Circuit opened - Redis appears down")

    # Calls blocked while circuit open
    with pytest.raises(ConnectionError) as exc_info:
        await circuit.call(redis_set_with_failure, "blocked_key", "value", should_fail=False)
    assert "Circuit breaker OPEN" in str(exc_info.value)

    # Wait for recovery
    time.sleep(0.6)

    # Redis "recovers" - successful call closes circuit
    await circuit.call(redis_set_with_failure, "recovery_key", "success", should_fail=False)
    assert circuit.state == CircuitState.CLOSED

    # Verify Redis actually worked (redis_clean has decode_responses=True, returns strings)
    result = redis_clean.get("recovery_key")
    assert result == "success"

    print(f"✅ Circuit closed - Redis recovered")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_independent_circuit_breakers_per_service():
    """
    Test that different services have independent circuit breakers.
    
    One service failing shouldn't affect others.
    """

    class ServiceA:
        def __init__(self):
            self.call_count = 0

        def call(self, should_fail: bool):
            self.call_count += 1
            if should_fail:
                raise ConnectionError("Service A failed")
            return "A_OK"

    class ServiceB:
        def __init__(self):
            self.call_count = 0

        def call(self, should_fail: bool):
            self.call_count += 1
            if should_fail:
                raise ConnectionError("Service B failed")
            return "B_OK"

    service_a = ServiceA()
    service_b = ServiceB()

    circuit_a = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    circuit_b = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

    # Fail service A only
    for i in range(3):
        with pytest.raises(ConnectionError):
            await circuit_a.call(service_a.call, should_fail=True)

    assert circuit_a.state == CircuitState.OPEN
    assert circuit_b.state == CircuitState.CLOSED  # B still healthy

    # Service A blocked
    with pytest.raises(ConnectionError):
        await circuit_a.call(service_a.call, should_fail=False)

    # Service B still works
    result = await circuit_b.call(service_b.call, should_fail=False)
    assert result == "B_OK"
    assert circuit_b.state == CircuitState.CLOSED

    assert service_a.call_count == 3  # Blocked after 3 failures
    assert service_b.call_count == 1  # Working normally

    print(f"✅ Independent circuit breakers: Service A blocked, Service B operational")
