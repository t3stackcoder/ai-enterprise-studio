"""
Timeout Handling Tests

Tests timeout behavior for slow operations.
Validates request timeouts, cleanup, and graceful degradation.
"""

import os
import sys
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

import asyncio
import time
from dataclasses import dataclass
from uuid import uuid4

import pytest
from buildingblocks.cqrs import ICommand, ICommandHandler, IQuery, IQueryHandler


# ============================================================================
# Commands & Queries
# ============================================================================


@dataclass
class SlowUploadCommand(ICommand):
    """Upload that takes time"""

    object_name: str
    delay: float  # Seconds to delay


@dataclass
class SlowSearchQuery(IQuery[list]):
    """Search that may timeout"""

    query: str
    delay: float


# ============================================================================
# Handlers
# ============================================================================


class SlowUploadHandler(ICommandHandler):
    """Handler that simulates slow uploads"""

    def __init__(self):
        self.completed_uploads = []
        self.cancelled_uploads = []

    async def handle(self, command: SlowUploadCommand) -> None:
        try:
            await asyncio.sleep(command.delay)
            self.completed_uploads.append(command.object_name)
        except asyncio.CancelledError:
            self.cancelled_uploads.append(command.object_name)
            raise


class SlowSearchHandler(IQueryHandler):
    """Handler that simulates slow searches"""

    def __init__(self):
        self.search_count = 0

    async def handle(self, query: SlowSearchQuery) -> list:
        self.search_count += 1
        await asyncio.sleep(query.delay)
        return [f"result_for_{query.query}"]


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_timeout_cancels_slow_operation():
    """
    Test that slow operations are cancelled after timeout.
    
    Scenario: Operation takes 5s, timeout after 1s → Cancelled.
    """
    handler = SlowUploadHandler()

    command = SlowUploadCommand(object_name="slow_file.txt", delay=5.0)

    start = time.time()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(handler.handle(command), timeout=1.0)

    elapsed = time.time() - start

    # Should timeout after ~1 second, not wait full 5 seconds
    assert 0.9 < elapsed < 1.5
    assert len(handler.completed_uploads) == 0  # Didn't complete
    assert len(handler.cancelled_uploads) == 1  # Was cancelled

    print(f"✅ Operation cancelled after {elapsed:.2f}s (timeout 1.0s)")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_fast_operation_completes_before_timeout():
    """
    Test that fast operations complete successfully within timeout.
    
    Scenario: Operation takes 0.1s, timeout 2s → Success.
    """
    handler = SlowUploadHandler()

    command = SlowUploadCommand(object_name="fast_file.txt", delay=0.1)

    # Should complete successfully
    await asyncio.wait_for(handler.handle(command), timeout=2.0)

    assert len(handler.completed_uploads) == 1
    assert "fast_file.txt" in handler.completed_uploads

    print(f"✅ Fast operation completed within timeout")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_timeout_with_fallback_to_cache(redis_clean):
    """
    Test timeout with fallback to cached results.
    
    Scenario: Search times out → Return cached results instead.
    """
    # Seed cache with fallback data
    cache_key = "search:backup_results"
    redis_clean.set(cache_key, "cached_result_1,cached_result_2")

    handler = SlowSearchHandler()

    # Attempt slow search with timeout
    try:
        query = SlowSearchQuery(query="slow_query", delay=3.0)
        results = await asyncio.wait_for(handler.handle(query), timeout=0.5)
    except asyncio.TimeoutError:
        # Fallback to cache (redis_clean has decode_responses=True, so returns strings)
        cached = redis_clean.get(cache_key)
        results = cached.split(",") if cached else []

    # Should have fallback results from cache
    assert len(results) == 2
    assert results[0] == "cached_result_1"
    assert handler.search_count == 1  # Search was attempted

    print(f"✅ Timeout handled gracefully with cache fallback")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_partial_results_on_timeout():
    """
    Test returning partial results when full query times out.
    
    Scenario: Multi-source search, some sources timeout → Return what we have.
    """

    async def search_source_a():
        await asyncio.sleep(0.1)
        return ["result_a1", "result_a2"]

    async def search_source_b():
        await asyncio.sleep(5.0)  # Too slow
        return ["result_b1", "result_b2"]

    async def search_source_c():
        await asyncio.sleep(0.2)
        return ["result_c1"]

    # Gather results with timeout
    tasks = [
        asyncio.create_task(search_source_a()),
        asyncio.create_task(search_source_b()),
        asyncio.create_task(search_source_c()),
    ]

    results = []
    done, pending = await asyncio.wait(tasks, timeout=1.0)

    # Collect completed results
    for task in done:
        try:
            results.extend(await task)
        except Exception:
            pass

    # Cancel pending tasks
    for task in pending:
        task.cancel()

    # Should have results from A and C, but not slow B
    assert len(results) == 3
    assert "result_a1" in results
    assert "result_c1" in results
    assert "result_b1" not in results

    print(f"✅ Partial results returned: {len(results)} items from {len(done)} sources")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_timeout_with_resource_cleanup():
    """
    Test that resources are cleaned up when operation times out.
    
    Ensures no resource leaks on timeout.
    """

    class ResourceHandler:
        def __init__(self):
            self.resources_opened = []
            self.resources_closed = []

        async def process_with_timeout(self, resource_id: str, delay: float):
            self.resources_opened.append(resource_id)
            try:
                await asyncio.sleep(delay)
                return "success"
            except asyncio.CancelledError:
                # Cleanup on cancellation
                self.resources_closed.append(resource_id)
                raise
            finally:
                # Always close
                if resource_id not in self.resources_closed:
                    self.resources_closed.append(resource_id)

    handler = ResourceHandler()

    # Start slow operation
    resource_id = "connection_123"
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(handler.process_with_timeout(resource_id, 3.0), timeout=0.5)

    # Verify cleanup happened
    assert resource_id in handler.resources_opened
    assert resource_id in handler.resources_closed

    print(f"✅ Resources cleaned up after timeout")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_cascading_timeouts():
    """
    Test that timeouts don't cascade and block entire pipeline.
    
    Scenario: One slow step shouldn't block other independent steps.
    """

    async def step_a():
        await asyncio.sleep(0.1)
        return "A_complete"

    async def step_b_slow():
        await asyncio.sleep(5.0)  # Too slow
        return "B_complete"

    async def step_c():
        await asyncio.sleep(0.1)
        return "C_complete"

    # Run steps independently with individual timeouts
    results = {}

    try:
        results["a"] = await asyncio.wait_for(step_a(), timeout=1.0)
    except asyncio.TimeoutError:
        results["a"] = "A_timeout"

    try:
        results["b"] = await asyncio.wait_for(step_b_slow(), timeout=1.0)
    except asyncio.TimeoutError:
        results["b"] = "B_timeout"

    try:
        results["c"] = await asyncio.wait_for(step_c(), timeout=1.0)
    except asyncio.TimeoutError:
        results["c"] = "C_timeout"

    # A and C should succeed, only B times out
    assert results["a"] == "A_complete"
    assert results["b"] == "B_timeout"
    assert results["c"] == "C_complete"

    print(f"✅ Independent timeouts: 2 succeeded, 1 timed out without blocking others")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_timeout_with_qdrant_search(qdrant_clean):
    """
    Test timeout handling with actual Qdrant vector search.
    
    Simulates slow search that needs timeout.
    """
    from qdrant_client.models import Distance, PointStruct, VectorParams

    # Setup collection
    collection_name = f"test_timeout_{uuid4().hex[:8]}"
    qdrant_clean.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=128, distance=Distance.COSINE),
    )

    # Insert many vectors (makes search slower)
    points = [
        PointStruct(id=str(uuid4()), vector=[0.1 * i] * 128, payload={"idx": i})
        for i in range(100)
    ]
    qdrant_clean.upsert(collection_name=collection_name, points=points)

    async def slow_search():
        # Simulate processing delay
        await asyncio.sleep(2.0)
        return qdrant_clean.search(
            collection_name=collection_name, query_vector=[0.5] * 128, limit=10
        )

    # Search with timeout
    start = time.time()
    try:
        results = await asyncio.wait_for(slow_search(), timeout=1.0)
    except asyncio.TimeoutError:
        results = []  # Return empty on timeout

    elapsed = time.time() - start

    assert elapsed < 1.5  # Stopped before 2s delay completed
    assert len(results) == 0  # Timeout before results

    print(f"✅ Qdrant search timeout handled ({elapsed:.2f}s)")


@pytest.mark.resilience
@pytest.mark.asyncio
async def test_adaptive_timeout_based_on_history():
    """
    Test adaptive timeout that adjusts based on historical performance.
    
    Fast operations get shorter timeout, slow ones get more time.
    """

    class AdaptiveTimeoutHandler:
        def __init__(self):
            self.execution_times = []
            self.default_timeout = 2.0

        def calculate_timeout(self) -> float:
            """Calculate timeout based on historical average + margin"""
            if not self.execution_times:
                return self.default_timeout

            avg = sum(self.execution_times) / len(self.execution_times)
            return avg * 2.0  # 2x average as timeout

        async def execute_with_adaptive_timeout(self, delay: float):
            timeout = self.calculate_timeout()
            start = time.time()

            try:
                await asyncio.wait_for(asyncio.sleep(delay), timeout=timeout)
                elapsed = time.time() - start
                self.execution_times.append(elapsed)
                return "success"
            except asyncio.TimeoutError:
                return "timeout"

    handler = AdaptiveTimeoutHandler()

    # First few fast operations
    for _ in range(5):
        result = await handler.execute_with_adaptive_timeout(0.1)
        assert result == "success"

    # Timeout adapts to fast operations
    adaptive_timeout = handler.calculate_timeout()
    assert adaptive_timeout < 1.0  # Much shorter than default 2.0s

    # Slow operation now times out with adaptive timeout
    result = await handler.execute_with_adaptive_timeout(5.0)
    assert result == "timeout"

    print(f"✅ Adaptive timeout: {adaptive_timeout:.2f}s (based on {len(handler.execution_times)} operations)")
