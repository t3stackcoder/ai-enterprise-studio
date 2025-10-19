"""
E2E Video Analysis Workflow Tests

Tests complete video analysis pipeline:
1. Upload video to MinIO
2. Extract/store embeddings in Qdrant
3. Cache metadata in Redis
4. Search for similar videos

Services: MinIO + Qdrant + Redis
"""

import os
import sys
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

import io
import json
from dataclasses import dataclass, field
from uuid import uuid4

import pytest
from buildingblocks.cqrs import ICommand, ICommandHandler, IQuery, IQueryHandler
from qdrant_client.models import Distance, PointStruct, VectorParams


# ============================================================================
# Commands
# ============================================================================


@dataclass
class UploadVideoCommand(ICommand):
    """Upload video file to storage"""

    video_id: str
    bucket_name: str
    object_name: str
    video_data: bytes


@dataclass
class StoreVideoEmbeddingCommand(ICommand):
    """Store video embedding in vector database"""

    video_id: str
    collection_name: str
    embedding: list[float]
    metadata: dict


@dataclass
class CacheVideoMetadataCommand(ICommand):
    """Cache video metadata in Redis"""

    video_id: str
    metadata: dict


# ============================================================================
# Queries
# ============================================================================


@dataclass
class SearchSimilarVideosQuery(IQuery[list]):
    """Search for similar videos by embedding"""

    collection_name: str
    query_embedding: list[float]
    limit: int = 5


@dataclass
class GetVideoMetadataQuery(IQuery[dict | None]):
    """Get video metadata from cache"""

    video_id: str


# ============================================================================
# Handlers
# ============================================================================


class UploadVideoHandler(ICommandHandler):
    """Handler for uploading videos to MinIO"""

    def __init__(self, minio_client):
        self.minio = minio_client

    async def handle(self, command: UploadVideoCommand) -> None:
        data_stream = io.BytesIO(command.video_data)
        self.minio.put_object(
            bucket_name=command.bucket_name,
            object_name=command.object_name,
            data=data_stream,
            length=len(command.video_data),
            content_type="video/mp4",
        )


class StoreVideoEmbeddingHandler(ICommandHandler):
    """Handler for storing video embeddings in Qdrant"""

    def __init__(self, qdrant_client):
        self.qdrant = qdrant_client

    async def handle(self, command: StoreVideoEmbeddingCommand) -> None:
        point = PointStruct(
            id=command.video_id, vector=command.embedding, payload=command.metadata
        )
        self.qdrant.upsert(collection_name=command.collection_name, points=[point])


class CacheVideoMetadataHandler(ICommandHandler):
    """Handler for caching video metadata in Redis"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def handle(self, command: CacheVideoMetadataCommand) -> None:
        cache_key = f"video:metadata:{command.video_id}"
        self.redis.setex(cache_key, 3600, json.dumps(command.metadata))  # 1 hour TTL


class SearchSimilarVideosHandler(IQueryHandler):
    """Handler for searching similar videos in Qdrant"""

    def __init__(self, qdrant_client):
        self.qdrant = qdrant_client

    async def handle(self, query: SearchSimilarVideosQuery) -> list:
        results = self.qdrant.search(
            collection_name=query.collection_name,
            query_vector=query.query_embedding,
            limit=query.limit,
        )
        return results


class GetVideoMetadataHandler(IQueryHandler):
    """Handler for retrieving video metadata from Redis cache"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def handle(self, query: GetVideoMetadataQuery) -> dict | None:
        cache_key = f"video:metadata:{query.video_id}"
        cached = self.redis.get(cache_key)
        return json.loads(cached) if cached else None


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_video_analysis_workflow(
    minio_clean, qdrant_clean, redis_clean, mediator
):
    """
    Complete E2E workflow: Upload video → Store embedding → Cache metadata → Search
    
    This simulates a real video analysis pipeline using all three services.
    """
    # Setup: Create Qdrant collection
    collection_name = f"test_videos_{uuid4().hex[:8]}"
    qdrant_clean.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=128, distance=Distance.COSINE),
    )

    # Register all handlers
    test_bucket = os.getenv("MINIO_TEST_BUCKET", "test-artifacts")
    mediator.register_command_handler(UploadVideoCommand, UploadVideoHandler(minio_clean))
    mediator.register_command_handler(
        StoreVideoEmbeddingCommand, StoreVideoEmbeddingHandler(qdrant_clean)
    )
    mediator.register_command_handler(
        CacheVideoMetadataCommand, CacheVideoMetadataHandler(redis_clean)
    )
    mediator.register_query_handler(
        SearchSimilarVideosQuery, SearchSimilarVideosHandler(qdrant_clean)
    )
    mediator.register_query_handler(
        GetVideoMetadataQuery, GetVideoMetadataHandler(redis_clean)
    )

    # Step 1: Upload video to MinIO
    video_id = str(uuid4())
    video_data = b"fake video content for testing"
    object_name = f"videos/{video_id}.mp4"

    await mediator.send_command(
        UploadVideoCommand(
            video_id=video_id,
            bucket_name=test_bucket,
            object_name=object_name,
            video_data=video_data,
        )
    )
    print(f"✅ Step 1: Uploaded video to MinIO: {object_name}")

    # Step 2: Store video embedding in Qdrant
    # Simulate embedding extraction (in real app, this would be GPU processing)
    embedding = [0.1] * 128  # 128-dim vector
    metadata = {
        "video_id": video_id,
        "filename": "test_video.mp4",
        "duration": 120,
        "upload_time": "2025-10-19T12:00:00Z",
    }

    await mediator.send_command(
        StoreVideoEmbeddingCommand(
            video_id=video_id,
            collection_name=collection_name,
            embedding=embedding,
            metadata=metadata,
        )
    )
    print(f"✅ Step 2: Stored embedding in Qdrant: {video_id}")

    # Step 3: Cache metadata in Redis
    await mediator.send_command(
        CacheVideoMetadataCommand(video_id=video_id, metadata=metadata)
    )
    print(f"✅ Step 3: Cached metadata in Redis: {video_id}")

    # Step 4: Search for similar videos
    query_embedding = [0.1] * 128  # Same embedding should find itself
    results = await mediator.send_query(
        SearchSimilarVideosQuery(
            collection_name=collection_name, query_embedding=query_embedding, limit=5
        )
    )

    # Verify search results
    assert len(results) > 0
    assert results[0].id == video_id
    assert results[0].payload["filename"] == "test_video.mp4"
    print(f"✅ Step 4: Found similar videos: {len(results)} results")

    # Step 5: Retrieve metadata from cache (cache hit)
    cached_metadata = await mediator.send_query(GetVideoMetadataQuery(video_id=video_id))

    assert cached_metadata is not None
    assert cached_metadata["video_id"] == video_id
    assert cached_metadata["filename"] == "test_video.mp4"
    print(f"✅ Step 5: Retrieved metadata from cache (cache hit)")

    print(f"🎉 Complete E2E workflow successful for video: {video_id}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cache_miss_scenario(redis_clean, mediator):
    """
    Test cache miss scenario - query for non-existent video metadata.
    """
    mediator.register_query_handler(
        GetVideoMetadataQuery, GetVideoMetadataHandler(redis_clean)
    )

    nonexistent_video_id = str(uuid4())
    cached_metadata = await mediator.send_query(
        GetVideoMetadataQuery(video_id=nonexistent_video_id)
    )

    assert cached_metadata is None
    print(f"✅ Cache miss handled correctly for video: {nonexistent_video_id}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_multiple_videos_search(minio_clean, qdrant_clean, mediator):
    """
    Test uploading multiple videos and searching across them.
    
    This tests multi-document workflows.
    """
    # Setup: Create collection
    collection_name = f"test_multi_videos_{uuid4().hex[:8]}"
    qdrant_clean.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=4, distance=Distance.COSINE),
    )

    # Register handlers
    test_bucket = os.getenv("MINIO_TEST_BUCKET", "test-artifacts")
    mediator.register_command_handler(UploadVideoCommand, UploadVideoHandler(minio_clean))
    mediator.register_command_handler(
        StoreVideoEmbeddingCommand, StoreVideoEmbeddingHandler(qdrant_clean)
    )
    mediator.register_query_handler(
        SearchSimilarVideosQuery, SearchSimilarVideosHandler(qdrant_clean)
    )

    # Upload and store 3 videos with different embeddings
    videos = [
        ([1.0, 0.0, 0.0, 0.0], "action_movie.mp4"),
        ([0.9, 0.1, 0.0, 0.0], "similar_action.mp4"),  # Similar to first
        ([0.0, 0.0, 1.0, 0.0], "documentary.mp4"),  # Different
    ]

    video_ids = []
    for embedding, filename in videos:
        video_id = str(uuid4())
        video_ids.append(video_id)

        # Upload to MinIO
        await mediator.send_command(
            UploadVideoCommand(
                video_id=video_id,
                bucket_name=test_bucket,
                object_name=f"videos/{filename}",
                video_data=b"fake video data",
            )
        )

        # Store embedding
        await mediator.send_command(
            StoreVideoEmbeddingCommand(
                video_id=video_id,
                collection_name=collection_name,
                embedding=embedding,
                metadata={"filename": filename},
            )
        )

    print(f"✅ Uploaded and indexed {len(videos)} videos")

    # Search for videos similar to first one
    query_embedding = [1.0, 0.0, 0.0, 0.0]
    results = await mediator.send_query(
        SearchSimilarVideosQuery(
            collection_name=collection_name, query_embedding=query_embedding, limit=2
        )
    )

    # Verify: Should find action movies, not documentary
    assert len(results) >= 2
    assert "action" in results[0].payload["filename"].lower()
    assert "action" in results[1].payload["filename"].lower()

    print(f"✅ Search found correct similar videos (action movies, not documentary)")
