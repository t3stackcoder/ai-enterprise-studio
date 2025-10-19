"""
Docker service fixtures for integration tests

Provides pytest fixtures for connecting to Docker services:
- Redis (cache, message broker)
- Qdrant (vector database)
- MinIO (S3-compatible storage)
- MLflow (model tracking)
"""

import os
import sys
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

import asyncio
from typing import Generator

import pytest
import redis
from dotenv import load_dotenv
from minio import Minio
from qdrant_client import QdrantClient

# Load test environment
env_path = project_root / ".env.test"
load_dotenv(env_path)


@pytest.fixture(scope="session")
def redis_client() -> Generator[redis.Redis, None, None]:
    """
    Session-scoped Redis client fixture.
    Connects to dev Redis instance but uses separate DB for tests.
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/1")
    client = redis.from_url(redis_url, decode_responses=True)

    # Verify connection
    try:
        client.ping()
        print(f"✅ Connected to Redis: {redis_url}")
    except redis.ConnectionError as e:
        pytest.fail(f"❌ Redis connection failed: {e}\nEnsure Docker services are running!")

    yield client

    # Cleanup: Flush test database after session
    if os.getenv("TEST_CLEANUP_ENABLED", "true").lower() == "true":
        client.flushdb()
        print("🧹 Cleaned up Redis test database")

    client.close()


@pytest.fixture(scope="function")
def redis_clean(redis_client: redis.Redis) -> Generator[redis.Redis, None, None]:
    """
    Function-scoped Redis fixture with automatic cleanup after each test.
    """
    # Clear before test
    redis_client.flushdb()

    yield redis_client

    # Clear after test
    redis_client.flushdb()


@pytest.fixture(scope="session")
def qdrant_client() -> Generator[QdrantClient, None, None]:
    """
    Session-scoped Qdrant client fixture.
    """
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))

    client = QdrantClient(host=host, port=port)

    # Verify connection
    try:
        collections = client.get_collections()
        print(f"✅ Connected to Qdrant: {host}:{port} ({len(collections.collections)} collections)")
    except Exception as e:
        pytest.fail(f"❌ Qdrant connection failed: {e}\nEnsure Docker services are running!")

    yield client

    # Cleanup: Delete test collections
    if os.getenv("TEST_CLEANUP_ENABLED", "true").lower() == "true":
        collections = client.get_collections()
        for collection in collections.collections:
            if collection.name.startswith("test_"):
                client.delete_collection(collection.name)
                print(f"🧹 Deleted Qdrant collection: {collection.name}")


@pytest.fixture(scope="function")
def qdrant_clean(qdrant_client: QdrantClient) -> Generator[QdrantClient, None, None]:
    """
    Function-scoped Qdrant fixture with automatic collection cleanup.
    """
    # Track collections created during test
    initial_collections = {c.name for c in qdrant_client.get_collections().collections}

    yield qdrant_client

    # Cleanup: Delete collections created during test
    final_collections = {c.name for c in qdrant_client.get_collections().collections}
    new_collections = final_collections - initial_collections

    for collection_name in new_collections:
        qdrant_client.delete_collection(collection_name)
        print(f"🧹 Cleaned up Qdrant collection: {collection_name}")


@pytest.fixture(scope="session")
def minio_client() -> Generator[Minio, None, None]:
    """
    Session-scoped MinIO client fixture.
    """
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
    secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

    client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

    # Verify connection
    try:
        buckets = client.list_buckets()
        print(f"✅ Connected to MinIO: {endpoint} ({len(buckets)} buckets)")
    except Exception as e:
        pytest.fail(f"❌ MinIO connection failed: {e}\nEnsure Docker services are running!")

    # Ensure test bucket exists
    test_bucket = os.getenv("MINIO_TEST_BUCKET", "test-artifacts")
    if not client.bucket_exists(test_bucket):
        client.make_bucket(test_bucket)
        print(f"📦 Created MinIO test bucket: {test_bucket}")

    yield client

    # Cleanup: Remove test objects
    if os.getenv("TEST_CLEANUP_ENABLED", "true").lower() == "true":
        test_bucket = os.getenv("MINIO_TEST_BUCKET", "test-artifacts")
        if client.bucket_exists(test_bucket):
            # Remove all objects in test bucket
            objects = client.list_objects(test_bucket, recursive=True)
            for obj in objects:
                client.remove_object(test_bucket, obj.object_name)
            print(f"🧹 Cleaned up MinIO test bucket: {test_bucket}")


@pytest.fixture(scope="function")
def minio_clean(minio_client: Minio) -> Generator[Minio, None, None]:
    """
    Function-scoped MinIO fixture with automatic object cleanup.
    """
    test_bucket = os.getenv("MINIO_TEST_BUCKET", "test-artifacts")

    # Clear bucket before test
    if minio_client.bucket_exists(test_bucket):
        objects = minio_client.list_objects(test_bucket, recursive=True)
        for obj in objects:
            minio_client.remove_object(test_bucket, obj.object_name)

    yield minio_client

    # Clear bucket after test
    if minio_client.bucket_exists(test_bucket):
        objects = minio_client.list_objects(test_bucket, recursive=True)
        for obj in objects:
            minio_client.remove_object(test_bucket, obj.object_name)


@pytest.fixture(scope="session")
def mlflow_client():
    """
    Session-scoped MLflow client fixture.
    """
    import mlflow

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)

    # Verify connection
    try:
        experiments = mlflow.search_experiments()
        print(f"✅ Connected to MLflow: {tracking_uri} ({len(experiments)} experiments)")
    except Exception as e:
        pytest.fail(f"❌ MLflow connection failed: {e}\nEnsure Docker services are running!")

    yield mlflow

    # Cleanup: Delete test experiments
    if os.getenv("TEST_CLEANUP_ENABLED", "true").lower() == "true":
        experiments = mlflow.search_experiments()
        for exp in experiments:
            if exp.name.startswith("test_"):
                mlflow.delete_experiment(exp.experiment_id)
                print(f"🧹 Deleted MLflow experiment: {exp.name}")


@pytest.fixture(scope="function")
def mlflow_clean(mlflow_client):
    """
    Function-scoped MLflow fixture with automatic experiment cleanup.
    """
    # Track experiments created during test
    initial_experiments = {exp.name for exp in mlflow_client.search_experiments()}

    yield mlflow_client

    # Cleanup: Delete experiments created during test
    final_experiments = {exp.name for exp in mlflow_client.search_experiments()}
    new_experiments = final_experiments - initial_experiments

    for exp_name in new_experiments:
        exp = mlflow_client.get_experiment_by_name(exp_name)
        mlflow_client.delete_experiment(exp.experiment_id)
        print(f"🧹 Cleaned up MLflow experiment: {exp_name}")


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for async tests.
    Required for pytest-asyncio with session-scoped fixtures.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
