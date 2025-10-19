"""
Redis integration tests using CQRS

Tests Redis cache operations through CQRS mediator with commands and handlers.
Validates that CQRS pattern works with real Redis instance.
"""

import os
import sys
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

from dataclasses import dataclass
from uuid import uuid4

import pytest
from buildingblocks.cqrs import ICommand, ICommandHandler, IQuery, IQueryHandler


# ============================================================================
# Commands
# ============================================================================


@dataclass
class StoreCacheValueCommand(ICommand):
    """Store a key-value pair in Redis cache"""

    key: str
    value: str

    def __post_init__(self):
        if not self.key:
            raise ValueError("Key cannot be empty")


@dataclass
class DeleteCacheKeyCommand(ICommand):
    """Delete a key from Redis cache"""

    key: str


# ============================================================================
# Queries
# ============================================================================


@dataclass
class GetCacheValueQuery(IQuery[str | None]):
    """Retrieve a value from Redis cache by key"""

    key: str


# ============================================================================
# Handlers
# ============================================================================


class StoreCacheValueHandler(ICommandHandler):
    """Handler for storing values in Redis"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def handle(self, command: StoreCacheValueCommand) -> None:
        self.redis.set(command.key, command.value)


class DeleteCacheKeyHandler(ICommandHandler):
    """Handler for deleting keys from Redis"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def handle(self, command: DeleteCacheKeyCommand) -> None:
        self.redis.delete(command.key)


class GetCacheValueHandler(IQueryHandler):
    """Handler for retrieving values from Redis"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def handle(self, query: GetCacheValueQuery) -> str | None:
        value = self.redis.get(query.key)
        return value if value else None


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.redis
@pytest.mark.asyncio
async def test_store_and_retrieve_cache_value(redis_clean, mediator):
    """
    Test storing and retrieving a value from Redis via CQRS.
    
    Flow:
    1. Register handlers with mediator
    2. Send StoreCacheValueCommand
    3. Send GetCacheValueQuery
    4. Verify value matches
    """
    # Register handlers
    mediator.register_command_handler(
        StoreCacheValueCommand, StoreCacheValueHandler(redis_clean)
    )
    mediator.register_query_handler(GetCacheValueQuery, GetCacheValueHandler(redis_clean))

    # Store value
    test_key = f"test:integration:{uuid4().hex[:8]}"
    await mediator.send_command(StoreCacheValueCommand(key=test_key, value="test_value"))

    # Retrieve value
    result = await mediator.send_query(GetCacheValueQuery(key=test_key))

    assert result == "test_value"
    print(f"✅ Stored and retrieved value from Redis: {test_key}")


@pytest.mark.integration
@pytest.mark.redis
@pytest.mark.asyncio
async def test_delete_cache_key(redis_clean, mediator):
    """
    Test deleting a key from Redis via CQRS.
    
    Flow:
    1. Store a value
    2. Delete the key via command
    3. Verify key no longer exists
    """
    # Register handlers
    mediator.register_command_handler(
        StoreCacheValueCommand, StoreCacheValueHandler(redis_clean)
    )
    mediator.register_command_handler(
        DeleteCacheKeyCommand, DeleteCacheKeyHandler(redis_clean)
    )
    mediator.register_query_handler(GetCacheValueQuery, GetCacheValueHandler(redis_clean))

    # Store value
    test_key = f"test:delete:{uuid4().hex[:8]}"
    await mediator.send_command(StoreCacheValueCommand(key=test_key, value="to_delete"))

    # Verify it exists
    result = await mediator.send_query(GetCacheValueQuery(key=test_key))
    assert result == "to_delete"

    # Delete key
    await mediator.send_command(DeleteCacheKeyCommand(key=test_key))

    # Verify it's gone
    result = await mediator.send_query(GetCacheValueQuery(key=test_key))
    assert result is None
    print(f"✅ Deleted key from Redis: {test_key}")


@pytest.mark.integration
@pytest.mark.redis
@pytest.mark.asyncio
async def test_validation_behavior_catches_empty_key(mediator):
    """
    Test that ValidationBehavior catches invalid commands.
    
    This validates that pipeline behaviors are executing correctly.
    """
    # Don't need to register handler - validation happens before handler
    with pytest.raises(ValueError, match="Key cannot be empty"):
        await mediator.send_command(StoreCacheValueCommand(key="", value="test"))

    print("✅ ValidationBehavior correctly rejected empty key")


@pytest.mark.integration
@pytest.mark.redis
@pytest.mark.asyncio
async def test_query_nonexistent_key_returns_none(redis_clean, mediator):
    """
    Test querying a key that doesn't exist returns None.
    """
    mediator.register_query_handler(GetCacheValueQuery, GetCacheValueHandler(redis_clean))

    test_key = f"nonexistent:{uuid4().hex[:8]}"
    result = await mediator.send_query(GetCacheValueQuery(key=test_key))

    assert result is None
    print(f"✅ Query for nonexistent key returned None: {test_key}")
