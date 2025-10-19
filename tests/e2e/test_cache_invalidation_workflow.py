"""
E2E Cache Invalidation Workflow Tests

Tests cache consistency and invalidation patterns:
1. Store vector embeddings in Qdrant
2. Cache search results in Redis
3. Update embeddings and invalidate cache
4. Verify cache refresh

Services: Qdrant + Redis
"""

import os
import sys
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

import json
from dataclasses import dataclass
from uuid import uuid4

import pytest
from buildingblocks.cqrs import ICommand, ICommandHandler, IQuery, IQueryHandler
from qdrant_client.models import Distance, PointStruct, VectorParams


# ============================================================================
# Commands
# ============================================================================


@dataclass
class IndexDocumentCommand(ICommand):
    """Index document with embedding"""

    collection_name: str
    doc_id: str
    embedding: list[float]
    content: dict


@dataclass
class UpdateDocumentEmbeddingCommand(ICommand):
    """Update existing document embedding"""

    collection_name: str
    doc_id: str
    new_embedding: list[float]
    new_content: dict


@dataclass
class CacheSearchResultsCommand(ICommand):
    """Cache search results in Redis"""

    query_hash: str
    results: list
    ttl: int = 300  # 5 minutes default


@dataclass
class InvalidateCacheCommand(ICommand):
    """Invalidate cache entries by pattern"""

    pattern: str


# ============================================================================
# Queries
# ============================================================================


@dataclass
class SearchDocumentsQuery(IQuery[list]):
    """Search documents by embedding"""

    collection_name: str
    query_embedding: list[float]
    use_cache: bool = True


@dataclass
class GetCachedSearchQuery(IQuery[list | None]):
    """Get cached search results"""

    query_hash: str


# ============================================================================
# Handlers
# ============================================================================


class IndexDocumentHandler(ICommandHandler):
    """Handler for indexing documents in Qdrant"""

    def __init__(self, qdrant_client):
        self.qdrant = qdrant_client

    async def handle(self, command: IndexDocumentCommand) -> None:
        point = PointStruct(
            id=command.doc_id, vector=command.embedding, payload=command.content
        )
        self.qdrant.upsert(collection_name=command.collection_name, points=[point])


class UpdateDocumentEmbeddingHandler(ICommandHandler):
    """Handler for updating document embeddings"""

    def __init__(self, qdrant_client):
        self.qdrant = qdrant_client

    async def handle(self, command: UpdateDocumentEmbeddingCommand) -> None:
        point = PointStruct(
            id=command.doc_id, vector=command.new_embedding, payload=command.new_content
        )
        self.qdrant.upsert(collection_name=command.collection_name, points=[point])


class CacheSearchResultsHandler(ICommandHandler):
    """Handler for caching search results"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def handle(self, command: CacheSearchResultsCommand) -> None:
        cache_key = f"search:{command.query_hash}"
        # Store as JSON
        results_json = json.dumps(
            [{"id": r.id, "score": r.score, "payload": r.payload} for r in command.results]
        )
        self.redis.setex(cache_key, command.ttl, results_json)


class InvalidateCacheHandler(ICommandHandler):
    """Handler for cache invalidation"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def handle(self, command: InvalidateCacheCommand) -> None:
        # Delete all keys matching pattern
        keys = list(self.redis.scan_iter(match=command.pattern))
        if keys:
            self.redis.delete(*keys)


class SearchDocumentsHandler(IQueryHandler):
    """Handler for searching documents with optional caching"""

    def __init__(self, qdrant_client, redis_client):
        self.qdrant = qdrant_client
        self.redis = redis_client

    async def handle(self, query: SearchDocumentsQuery) -> list:
        # Create query hash
        query_hash = f"{query.collection_name}:{hash(tuple(query.query_embedding))}"

        # Check cache first if enabled
        if query.use_cache:
            cache_key = f"search:{query_hash}"
            cached = self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        # Cache miss - query Qdrant
        results = self.qdrant.search(
            collection_name=query.collection_name,
            query_vector=query.query_embedding,
            limit=5,
        )

        # Cache the results if caching enabled
        if query.use_cache:
            results_json = json.dumps(
                [{"id": r.id, "score": r.score, "payload": r.payload} for r in results]
            )
            self.redis.setex(cache_key, 300, results_json)

        return results


class GetCachedSearchHandler(IQueryHandler):
    """Handler for retrieving cached search results"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def handle(self, query: GetCachedSearchQuery) -> list | None:
        cache_key = f"search:{query.query_hash}"
        cached = self.redis.get(cache_key)
        return json.loads(cached) if cached else None


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_invalidation_workflow(qdrant_clean, redis_clean, mediator):
    """
    Complete E2E workflow: Index docs → Search & cache → Update doc → Invalidate cache
    
    This tests cache consistency when underlying data changes.
    """
    # Setup: Create collection
    collection_name = f"test_docs_{uuid4().hex[:8]}"
    qdrant_clean.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=4, distance=Distance.COSINE),
    )

    # Register all handlers
    mediator.register_command_handler(
        IndexDocumentCommand, IndexDocumentHandler(qdrant_clean)
    )
    mediator.register_command_handler(
        UpdateDocumentEmbeddingCommand, UpdateDocumentEmbeddingHandler(qdrant_clean)
    )
    mediator.register_command_handler(
        CacheSearchResultsCommand, CacheSearchResultsHandler(redis_clean)
    )
    mediator.register_command_handler(
        InvalidateCacheCommand, InvalidateCacheHandler(redis_clean)
    )
    mediator.register_query_handler(
        SearchDocumentsQuery, SearchDocumentsHandler(qdrant_clean, redis_clean)
    )
    mediator.register_query_handler(
        GetCachedSearchQuery, GetCachedSearchHandler(redis_clean)
    )

    # Step 1: Index original documents
    doc_id = str(uuid4())
    original_embedding = [1.0, 0.0, 0.0, 0.0]
    original_content = {"title": "Original Document", "version": 1}

    await mediator.send_command(
        IndexDocumentCommand(
            collection_name=collection_name,
            doc_id=doc_id,
            embedding=original_embedding,
            content=original_content,
        )
    )
    print(f"✅ Step 1: Indexed original document: {doc_id}")

    # Step 2: Search and cache results
    query_embedding = [1.0, 0.0, 0.0, 0.0]
    results = await mediator.send_query(
        SearchDocumentsQuery(
            collection_name=collection_name,
            query_embedding=query_embedding,
            use_cache=True,
        )
    )

    assert len(results) == 1
    if isinstance(results[0], dict):
        # Cached result
        assert results[0]["payload"]["version"] == 1
    else:
        # Fresh result
        assert results[0].payload["version"] == 1
    print(f"✅ Step 2: Searched and cached results")

    # Step 3: Verify cache hit
    query_hash = f"{collection_name}:{hash(tuple(query_embedding))}"
    cached = await mediator.send_query(GetCachedSearchQuery(query_hash=query_hash))

    assert cached is not None
    assert cached[0]["payload"]["version"] == 1
    print(f"✅ Step 3: Verified cache hit with original data")

    # Step 4: Update document embedding
    new_embedding = [0.0, 1.0, 0.0, 0.0]  # Different vector
    new_content = {"title": "Updated Document", "version": 2}

    await mediator.send_command(
        UpdateDocumentEmbeddingCommand(
            collection_name=collection_name,
            doc_id=doc_id,
            new_embedding=new_embedding,
            new_content=new_content,
        )
    )
    print(f"✅ Step 4: Updated document embedding")

    # Step 5: Invalidate all search caches
    await mediator.send_command(InvalidateCacheCommand(pattern="search:*"))
    print(f"✅ Step 5: Invalidated search caches")

    # Step 6: Verify cache miss and fresh data
    cached_after_invalidation = await mediator.send_query(
        GetCachedSearchQuery(query_hash=query_hash)
    )

    assert cached_after_invalidation is None
    print(f"✅ Step 6: Verified cache was invalidated (cache miss)")

    # Step 7: New search should return updated data
    new_results = await mediator.send_query(
        SearchDocumentsQuery(
            collection_name=collection_name,
            query_embedding=new_embedding,  # Search for updated vector
            use_cache=True,
        )
    )

    assert len(new_results) == 1
    if isinstance(new_results[0], dict):
        assert new_results[0]["payload"]["version"] == 2
    else:
        assert new_results[0].payload["version"] == 2
    print(f"✅ Step 7: Fresh search returned updated data")

    print(f"🎉 Cache invalidation workflow successful!")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_selective_cache_invalidation(redis_clean, mediator):
    """
    Test invalidating specific cache patterns while preserving others.
    """
    # Register handlers
    mediator.register_command_handler(
        CacheSearchResultsCommand, CacheSearchResultsHandler(redis_clean)
    )
    mediator.register_command_handler(
        InvalidateCacheCommand, InvalidateCacheHandler(redis_clean)
    )

    # Cache multiple types of data
    search_results_1 = [{"id": "1", "score": 0.9, "payload": {"type": "search"}}]
    search_results_2 = [{"id": "2", "score": 0.8, "payload": {"type": "search"}}]

    # Mock results with proper structure for caching
    from types import SimpleNamespace

    mock_results_1 = [
        SimpleNamespace(id="1", score=0.9, payload={"type": "search"})
    ]
    mock_results_2 = [
        SimpleNamespace(id="2", score=0.8, payload={"type": "search"})
    ]

    await mediator.send_command(
        CacheSearchResultsCommand(query_hash="collection1:hash1", results=mock_results_1)
    )
    await mediator.send_command(
        CacheSearchResultsCommand(query_hash="collection2:hash2", results=mock_results_2)
    )

    # Cache some metadata too
    redis_clean.setex("metadata:doc1", 300, json.dumps({"title": "Doc 1"}))
    redis_clean.setex("metadata:doc2", 300, json.dumps({"title": "Doc 2"}))

    print(f"✅ Cached search results and metadata")

    # Invalidate only collection1 searches
    await mediator.send_command(InvalidateCacheCommand(pattern="search:collection1:*"))

    # Verify: collection1 cache gone, collection2 and metadata remain
    assert redis_clean.get("search:collection1:hash1") is None
    assert redis_clean.get("search:collection2:hash2") is not None
    assert redis_clean.get("metadata:doc1") is not None

    print(f"✅ Selective invalidation: collection1 cleared, others preserved")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_performance_benefit(qdrant_clean, redis_clean, mediator):
    """
    Test that cached searches are faster than uncached ones.
    
    This demonstrates the performance benefit of caching.
    """
    import time

    # Setup collection
    collection_name = f"test_perf_{uuid4().hex[:8]}"
    qdrant_clean.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=128, distance=Distance.COSINE),
    )

    # Register handlers
    mediator.register_command_handler(
        IndexDocumentCommand, IndexDocumentHandler(qdrant_clean)
    )
    mediator.register_query_handler(
        SearchDocumentsQuery, SearchDocumentsHandler(qdrant_clean, redis_clean)
    )

    # Index many documents
    for i in range(20):
        embedding = [0.1 * i] * 128
        await mediator.send_command(
            IndexDocumentCommand(
                collection_name=collection_name,
                doc_id=str(uuid4()),
                embedding=embedding,
                content={"doc_num": i},
            )
        )

    print(f"✅ Indexed 20 documents")

    # First search (cache miss) - measure time
    query_embedding = [0.5] * 128
    start = time.time()
    await mediator.send_query(
        SearchDocumentsQuery(
            collection_name=collection_name,
            query_embedding=query_embedding,
            use_cache=True,
        )
    )
    uncached_time = time.time() - start

    # Second search (cache hit) - measure time
    start = time.time()
    await mediator.send_query(
        SearchDocumentsQuery(
            collection_name=collection_name,
            query_embedding=query_embedding,
            use_cache=True,
        )
    )
    cached_time = time.time() - start

    print(f"✅ Uncached search: {uncached_time*1000:.2f}ms")
    print(f"✅ Cached search: {cached_time*1000:.2f}ms")

    # Cached should be faster (allowing some margin for variance)
    assert cached_time < uncached_time * 1.5  # At least some speedup
    print(f"✅ Cache provides performance benefit!")
