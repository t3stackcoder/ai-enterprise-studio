"""
Qdrant integration tests using CQRS

Tests Qdrant vector database operations through CQRS mediator.
Validates vector storage, search, and collection management.
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
from qdrant_client.models import Distance, PointStruct, VectorParams


# ============================================================================
# Commands
# ============================================================================


@dataclass
class CreateCollectionCommand(ICommand):
    """Create a new vector collection in Qdrant"""

    collection_name: str
    vector_size: int = 128
    distance: str = "Cosine"


@dataclass
class StoreVectorCommand(ICommand):
    """Store a vector in Qdrant collection"""

    collection_name: str
    vector_id: str
    vector: list[float]
    payload: dict | None = None


@dataclass
class DeleteCollectionCommand(ICommand):
    """Delete a collection from Qdrant"""

    collection_name: str


# ============================================================================
# Queries
# ============================================================================


@dataclass
class SearchSimilarVectorsQuery(IQuery[list]):
    """Search for similar vectors in collection"""

    collection_name: str
    query_vector: list[float]
    limit: int = 5


# ============================================================================
# Handlers
# ============================================================================


class CreateCollectionHandler(ICommandHandler):
    """Handler for creating Qdrant collections"""

    def __init__(self, qdrant_client):
        self.qdrant = qdrant_client

    async def handle(self, command: CreateCollectionCommand) -> None:
        distance_map = {
            "Cosine": Distance.COSINE,
            "Euclidean": Distance.EUCLID,
            "Dot": Distance.DOT,
        }

        self.qdrant.create_collection(
            collection_name=command.collection_name,
            vectors_config=VectorParams(
                size=command.vector_size, distance=distance_map[command.distance]
            ),
        )


class StoreVectorHandler(ICommandHandler):
    """Handler for storing vectors in Qdrant"""

    def __init__(self, qdrant_client):
        self.qdrant = qdrant_client

    async def handle(self, command: StoreVectorCommand) -> None:
        point = PointStruct(
            id=command.vector_id, vector=command.vector, payload=command.payload or {}
        )
        self.qdrant.upsert(collection_name=command.collection_name, points=[point])


class DeleteCollectionHandler(ICommandHandler):
    """Handler for deleting Qdrant collections"""

    def __init__(self, qdrant_client):
        self.qdrant = qdrant_client

    async def handle(self, command: DeleteCollectionCommand) -> None:
        self.qdrant.delete_collection(command.collection_name)


class SearchSimilarVectorsHandler(IQueryHandler):
    """Handler for searching similar vectors"""

    def __init__(self, qdrant_client):
        self.qdrant = qdrant_client

    async def handle(self, query: SearchSimilarVectorsQuery) -> list:
        results = self.qdrant.search(
            collection_name=query.collection_name,
            query_vector=query.query_vector,
            limit=query.limit,
        )
        return results


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.qdrant
@pytest.mark.asyncio
async def test_create_collection(qdrant_clean, mediator):
    """
    Test creating a vector collection in Qdrant via CQRS.
    """
    mediator.register_command_handler(
        CreateCollectionCommand, CreateCollectionHandler(qdrant_clean)
    )

    collection_name = f"test_collection_{uuid4().hex[:8]}"
    await mediator.send_command(
        CreateCollectionCommand(collection_name=collection_name, vector_size=128)
    )

    # Verify collection exists
    collections = qdrant_clean.get_collections()
    collection_names = [c.name for c in collections.collections]
    assert collection_name in collection_names

    print(f"✅ Created Qdrant collection: {collection_name}")


@pytest.mark.integration
@pytest.mark.qdrant
@pytest.mark.asyncio
async def test_store_and_search_vectors(qdrant_clean, mediator):
    """
    Test storing vectors and searching for similar ones via CQRS.
    
    Flow:
    1. Create collection
    2. Store multiple vectors
    3. Search for similar vector
    4. Verify results
    """
    # Register handlers
    mediator.register_command_handler(
        CreateCollectionCommand, CreateCollectionHandler(qdrant_clean)
    )
    mediator.register_command_handler(StoreVectorCommand, StoreVectorHandler(qdrant_clean))
    mediator.register_query_handler(
        SearchSimilarVectorsQuery, SearchSimilarVectorsHandler(qdrant_clean)
    )

    # Create collection
    collection_name = f"test_search_{uuid4().hex[:8]}"
    vector_size = 4
    await mediator.send_command(
        CreateCollectionCommand(collection_name=collection_name, vector_size=vector_size)
    )

    # Store test vectors
    test_vectors = [
        ([1.0, 0.0, 0.0, 0.0], {"label": "vector_a"}),
        ([0.9, 0.1, 0.0, 0.0], {"label": "vector_b"}),  # Similar to first
        ([0.0, 0.0, 1.0, 0.0], {"label": "vector_c"}),  # Different
    ]

    for idx, (vector, payload) in enumerate(test_vectors):
        await mediator.send_command(
            StoreVectorCommand(
                collection_name=collection_name,
                vector_id=str(uuid4()),  # Use UUID for vector ID
                vector=vector,
                payload=payload,
            )
        )

    # Search for vectors similar to first one
    query_vector = [1.0, 0.0, 0.0, 0.0]
    results = await mediator.send_query(
        SearchSimilarVectorsQuery(
            collection_name=collection_name, query_vector=query_vector, limit=2
        )
    )

    # Verify results
    assert len(results) > 0
    # First result should be exact match or very similar
    assert results[0].payload["label"] in ["vector_a", "vector_b"]

    print(f"✅ Stored and searched vectors in Qdrant: {collection_name}")


@pytest.mark.integration
@pytest.mark.qdrant
@pytest.mark.asyncio
async def test_delete_collection(qdrant_clean, mediator):
    """
    Test deleting a collection from Qdrant via CQRS.
    """
    # Register handlers
    mediator.register_command_handler(
        CreateCollectionCommand, CreateCollectionHandler(qdrant_clean)
    )
    mediator.register_command_handler(
        DeleteCollectionCommand, DeleteCollectionHandler(qdrant_clean)
    )

    # Create collection
    collection_name = f"test_delete_{uuid4().hex[:8]}"
    await mediator.send_command(
        CreateCollectionCommand(collection_name=collection_name, vector_size=128)
    )

    # Verify it exists
    collections = qdrant_clean.get_collections()
    collection_names = [c.name for c in collections.collections]
    assert collection_name in collection_names

    # Delete collection
    await mediator.send_command(DeleteCollectionCommand(collection_name=collection_name))

    # Verify it's gone
    collections = qdrant_clean.get_collections()
    collection_names = [c.name for c in collections.collections]
    assert collection_name not in collection_names

    print(f"✅ Deleted Qdrant collection: {collection_name}")
