"""
Integration and E2E tests for AI Enterprise Studio

This test suite uses the buildingblocks CQRS infrastructure to test
Docker services (Redis, Qdrant, MinIO, MLflow) in isolation and in
complete end-to-end workflows.

Test Structure:
- integration/: Service-level tests for individual Docker services
- e2e/: End-to-end workflow tests combining multiple services
- fixtures/: Shared test fixtures and utilities

Markers:
- @pytest.mark.integration: Requires Docker services
- @pytest.mark.e2e: Full workflow tests
- @pytest.mark.redis: Redis-specific tests
- @pytest.mark.qdrant: Qdrant-specific tests
- @pytest.mark.minio: MinIO-specific tests
- @pytest.mark.mlflow: MLflow-specific tests
"""
