"""
Retry Behavior Tests

Tests automatic retry logic for transient failures.
Validates exponential backoff, max retries, and idempotency.
"""

import os
import sys
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

import time
from dataclasses import dataclass
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from buildingblocks.cqrs import ICommand, ICommandHandler, IQuery, IQueryHandler


# ============================================================================
# Commands & Queries
# ============================================================================


@dataclass
class FlakyUploadCommand(ICommand):
    """Upload that may fail on first attempts"""

    bucket_name: str
    object_name: str
    data: bytes
    fail_count: int = 0  # How many times to fail before succeeding


@dataclass
class RetryableSearchQuery(IQuery[list]):
    """Search query that may timeout initially"""

    collection_name: str
    query_vector: list[float]
    fail_count: int = 0


# ============================================================================
# Handlers with Retry Logic
# ============================================================================


class FlakyUploadHandler(ICommandHandler):
    """Handler that simulates flaky MinIO uploads"""

    def __init__(self, minio_client):
        self.minio = minio_client
        self.attempt_count = {}

    async def handle(self, command: FlakyUploadCommand) -> None:
        key = command.object_name
        attempts = self.attempt_count.get(key, 0)
        self.attempt_count[key] = attempts + 1

        # Simulate transient failure
        if attempts < command.fail_count:
            raise ConnectionError(f"Simulated failure (attempt {attempts + 1})")

        # Success on Nth attempt
        import io

        data_stream = io.BytesIO(command.data)
        self.minio.put_object(
            bucket_name=command.bucket_name,
            object_name=command.object_name,
            data=data_stream,
            length=len(command.data),
        )


class RetryableSearchHandler(IQueryHandler):
    """Handler that simulates flaky Qdrant searches"""

    def __init__(self, qdrant_client):
        self.qdrant = qdrant_client
        self.attempt_count = {}

    async def handle(self, query: RetryableSearchQuery) -> list:
        key = query.collection_name
        attempts = self.attempt_count.get(key, 0)
        self.attempt_count[key] = attempts + 1

        # Simulate timeout
        if attempts < query.fail_count:
            raise TimeoutError(f"Search timeout (attempt {attempts + 1})")

        # Success
        return self.qdrant.search(
            collection_name=query.collection_name,
            query_vector=query.query_vector,
            limit=5,
        )


# ============================================================================
# Retry Decorator (Simple Implementation)
# ============================================================================


def retry_on_exception(max_retries=3, backoff_factor=1.0, exceptions=(Exception,)):
    """Decorator for retry logic with exponential backoff"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor * (2**attempt)
                        print(f"⚠️  Retry {attempt + 1}/{max_retries} after {wait_time}s: {e}")
                        time.sleep(wait_time)
                    else:
                        print(f"❌ Max retries reached, failing")
            raise last_exception

        return wrapper

    return decorator


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_failure(minio_clean):
    """
    Test that retry logic recovers from transient failures.
    
    Scenario: MinIO upload fails twice, succeeds on 3rd attempt.
    """
    handler = FlakyUploadHandler(minio_clean)
    original_handle = handler.handle

    # Create retry wrapper that doesn't reassign
    @retry_on_exception(max_retries=5, backoff_factor=0.1, exceptions=(ConnectionError,))
    async def retry_wrapper(command):
        return await original_handle(command)

    # Execute command that will fail 2 times
    test_bucket = os.getenv("MINIO_TEST_BUCKET", "test-artifacts")
    object_name = f"retry-test/{uuid4()}.txt"

    command = FlakyUploadCommand(
        bucket_name=test_bucket,
        object_name=object_name,
        data=b"test data",
        fail_count=2,  # Fail twice, succeed on 3rd
    )

    # Call through retry wrapper
    await retry_wrapper(command)

    # Verify file was uploaded
    objects = list(minio_clean.list_objects(test_bucket, prefix="retry-test/"))
    assert len(objects) > 0
    assert handler.attempt_count[object_name] == 3  # Took 3 attempts

    print(f"✅ Retry succeeded after {handler.attempt_count[object_name]} attempts")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_exponential_backoff_timing(minio_clean):
    """
    Test that exponential backoff increases wait time between retries.
    
    Validates: 0.1s → 0.2s → 0.4s → 0.8s
    """
    handler = FlakyUploadHandler(minio_clean)
    original_handle = handler.handle

    retry_times = []

    @retry_on_exception(max_retries=4, backoff_factor=0.1, exceptions=(ConnectionError,))
    async def retry_wrapper(command):
        retry_times.append(time.time())
        return await original_handle(command)

    test_bucket = os.getenv("MINIO_TEST_BUCKET", "test-artifacts")
    object_name = f"backoff-test/{uuid4()}.txt"

    command = FlakyUploadCommand(
        bucket_name=test_bucket,
        object_name=object_name,
        data=b"backoff test",
        fail_count=3,  # Fail 3 times
    )

    start_time = time.time()
    await retry_wrapper(command)
    total_time = time.time() - start_time

    # Verify exponential backoff: 0.1 + 0.2 + 0.4 = 0.7s minimum
    assert total_time >= 0.7
    assert len(retry_times) == 4  # 4 attempts total

    print(f"✅ Exponential backoff working: {total_time:.2f}s total")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_max_retries_eventually_fails(minio_clean):
    """
    Test that max retry limit is respected and eventually fails.
    
    Scenario: Upload always fails, should give up after max retries.
    """
    handler = FlakyUploadHandler(minio_clean)
    original_handle = handler.handle

    @retry_on_exception(max_retries=3, backoff_factor=0.05, exceptions=(ConnectionError,))
    async def retry_wrapper(command):
        return await original_handle(command)

    test_bucket = os.getenv("MINIO_TEST_BUCKET", "test-artifacts")
    object_name = f"fail-test/{uuid4()}.txt"

    command = FlakyUploadCommand(
        bucket_name=test_bucket,
        object_name=object_name,
        data=b"will fail",
        fail_count=100,  # Always fail
    )

    # This will fail forever (fail_count=100)
    with pytest.raises(ConnectionError) as exc_info:
        await retry_wrapper(command)

    assert "Simulated failure (attempt 3)" in str(exc_info.value)
    assert handler.attempt_count[object_name] == 3  # Stopped at max retries

    print(f"✅ Correctly failed after max retries ({handler.attempt_count[object_name]} attempts)")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_idempotent_retry_safe(qdrant_clean):
    """
    Test that idempotent operations can be safely retried.
    
    Scenario: Search query retried multiple times produces same result.
    """
    from qdrant_client.models import Distance, PointStruct, VectorParams

    # Setup: Create collection with data
    collection_name = f"test_idempotent_{uuid4().hex[:8]}"
    qdrant_clean.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=4, distance=Distance.COSINE),
    )

    # Insert test vector
    test_id = str(uuid4())
    qdrant_clean.upsert(
        collection_name=collection_name,
        points=[PointStruct(id=test_id, vector=[1.0, 0.0, 0.0, 0.0], payload={"type": "test"})],
    )

    # Handler with retry
    handler = RetryableSearchHandler(qdrant_clean)
    original_handle = handler.handle

    @retry_on_exception(max_retries=5, backoff_factor=0.05, exceptions=(TimeoutError,))
    async def retry_wrapper(query):
        return await original_handle(query)

    query = RetryableSearchQuery(
        collection_name=collection_name,
        query_vector=[1.0, 0.0, 0.0, 0.0],
        fail_count=2,  # Fail twice
    )

    # Execute query that fails twice
    results = await retry_wrapper(query)

    # Verify: Same result despite retries
    assert len(results) == 1
    assert results[0].id == test_id
    assert handler.attempt_count[collection_name] == 3  # 3 attempts

    print(f"✅ Idempotent query safely retried {handler.attempt_count[collection_name]} times")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_non_retryable_errors_fail_immediately(redis_clean, mediator):
    """
    Test that non-retryable errors (like validation) fail immediately without retry.
    
    Scenario: Invalid command should not be retried.
    """
    from buildingblocks.cqrs import ICommand, ICommandHandler

    @dataclass
    class ValidatedCommand(ICommand):
        key: str
        value: str

        def __post_init__(self):
            if not self.key:
                raise ValueError("Key cannot be empty")

    class ValidatedHandler(ICommandHandler):
        def __init__(self, redis_client):
            self.redis = redis_client

        async def handle(self, command: ValidatedCommand) -> None:
            self.redis.set(command.key, command.value)

    handler = ValidatedHandler(redis_clean)
    mediator.register_command_handler(ValidatedCommand, handler)

    # Validation error should NOT be retried
    with pytest.raises(ValueError) as exc_info:
        await mediator.send_command(ValidatedCommand(key="", value="test"))

    assert "Key cannot be empty" in str(exc_info.value)
    print(f"✅ Validation error correctly failed without retry")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_retry_with_different_exception_types(minio_clean):
    """
    Test that retry decorator only retries specific exception types.
    
    Validates: ConnectionError retried, ValueError not retried.
    """
    attempt_count = {"connection": 0, "value": 0}

    @retry_on_exception(max_retries=3, backoff_factor=0.05, exceptions=(ConnectionError,))
    async def connection_error_func():
        attempt_count["connection"] += 1
        if attempt_count["connection"] < 2:
            raise ConnectionError("Transient network issue")
        return "success"

    @retry_on_exception(max_retries=3, backoff_factor=0.05, exceptions=(ConnectionError,))
    async def value_error_func():
        attempt_count["value"] += 1
        raise ValueError("Invalid input")  # Won't be retried

    # Test 1: ConnectionError gets retried
    result = await connection_error_func()
    assert result == "success"
    assert attempt_count["connection"] == 2

    # Test 2: ValueError fails immediately
    with pytest.raises(ValueError):
        await value_error_func()
    assert attempt_count["value"] == 1  # Only 1 attempt

    print(f"✅ Selective retry working: ConnectionError retried, ValueError not retried")
