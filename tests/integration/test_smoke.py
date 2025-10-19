"""
Smoke tests for Docker service connectivity

Simple tests to verify all Docker services are running and reachable.
No CQRS complexity - just basic connectivity validation.
"""

import pytest


@pytest.mark.smoke
@pytest.mark.redis
def test_redis_connection(redis_client):
    """
    Verify Redis is reachable and responding to commands.
    
    This test:
    - Connects to Redis on localhost:6379
    - Sends PING command
    - Expects PONG response
    """
    assert redis_client.ping() is True
    print("✅ Redis is connected and responding")


@pytest.mark.smoke
@pytest.mark.qdrant
def test_qdrant_connection(qdrant_client):
    """
    Verify Qdrant vector database is reachable.
    
    This test:
    - Connects to Qdrant on localhost:6333
    - Lists existing collections
    - Verifies API is responsive
    """
    collections = qdrant_client.get_collections()
    assert collections is not None
    print(f"✅ Qdrant is connected ({len(collections.collections)} collections)")


@pytest.mark.smoke
@pytest.mark.minio
def test_minio_connection(minio_client):
    """
    Verify MinIO S3-compatible storage is reachable.
    
    This test:
    - Connects to MinIO on localhost:9000
    - Lists existing buckets
    - Verifies S3 API is responsive
    """
    buckets = minio_client.list_buckets()
    assert buckets is not None
    print(f"✅ MinIO is connected ({len(buckets)} buckets)")


@pytest.mark.smoke
@pytest.mark.mlflow
def test_mlflow_connection(mlflow_client):
    """
    Verify MLflow tracking server is reachable.
    
    This test:
    - Connects to MLflow on localhost:5000
    - Lists existing experiments
    - Verifies tracking API is responsive
    """
    experiments = mlflow_client.search_experiments()
    assert experiments is not None
    print(f"✅ MLflow is connected ({len(experiments)} experiments)")


@pytest.mark.smoke
def test_all_services_healthy(redis_client, qdrant_client, minio_client, mlflow_client):
    """
    Comprehensive health check - all services must be operational.
    
    This test verifies all Docker services are running simultaneously.
    If this passes, the infrastructure is ready for integration tests.
    """
    # Redis
    assert redis_client.ping() is True
    
    # Qdrant
    collections = qdrant_client.get_collections()
    assert collections is not None
    
    # MinIO
    buckets = minio_client.list_buckets()
    assert buckets is not None
    
    # MLflow
    experiments = mlflow_client.search_experiments()
    assert experiments is not None
    
    print("✅ ALL SERVICES HEALTHY - Infrastructure is ready for integration tests!")
