"""
Root conftest.py for AI Enterprise Studio tests

Provides shared fixtures and configuration for all tests.
Imports fixtures from fixtures/ subdirectory.
"""

import os
import sys
from pathlib import Path

# Add libs to path FIRST
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "libs"))

from dotenv import load_dotenv

# Load test environment variables
env_path = project_root / ".env.test"
load_dotenv(env_path)

# Set testing flag
os.environ["TESTING"] = "true"

import pytest

# Import all fixtures from fixtures directory
# This makes them available to all tests
pytest_plugins = [
    "tests.fixtures.docker_fixtures",
    "tests.fixtures.cqrs_fixtures",
]


@pytest.fixture(autouse=True)
def test_environment():
    """
    Auto-used fixture that ensures test environment is properly configured.
    Runs before every test.
    """
    # Verify critical environment variables
    required_vars = [
        "REDIS_URL",
        "QDRANT_HOST",
        "MINIO_ENDPOINT",
        "MLFLOW_TRACKING_URI",
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        pytest.fail(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            f"Ensure .env.test is properly configured!"
        )

    yield

    # Cleanup after test (if needed)
    pass


def pytest_configure(config):
    """
    Pytest configuration hook.
    Called once at the start of the test session.
    """
    # Register custom markers
    config.addinivalue_line(
        "markers", "integration: Integration tests requiring Docker services"
    )
    config.addinivalue_line("markers", "e2e: End-to-end workflow tests")
    config.addinivalue_line("markers", "redis: Tests requiring Redis")
    config.addinivalue_line("markers", "qdrant: Tests requiring Qdrant")
    config.addinivalue_line("markers", "minio: Tests requiring MinIO")
    config.addinivalue_line("markers", "mlflow: Tests requiring MLflow")
    config.addinivalue_line("markers", "slow: Slow tests (>1 second)")
    config.addinivalue_line("markers", "unit: Unit tests without external dependencies")
    config.addinivalue_line("markers", "smoke: Quick smoke tests for CI/CD")

    print("\n" + "=" * 80)
    print("🚀 AI Enterprise Studio - Integration & E2E Tests")
    print("=" * 80)
    print(f"📁 Project Root: {project_root}")
    print(f"🔧 Test Environment: {env_path}")
    print(f"🐳 Docker Services: Redis, Qdrant, MinIO, MLflow")
    print(f"🏗️  CQRS Infrastructure: buildingblocks")
    print("=" * 80 + "\n")


def pytest_collection_modifyitems(config, items):
    """
    Modify test items after collection.
    Can be used to add markers, skip tests, etc.
    """
    # Add integration marker to tests in integration/ directory
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


@pytest.fixture(scope="session")
def docker_services_running():
    """
    Session-scoped fixture to verify Docker services are running.
    Fails fast if services are not available.
    """
    import socket

    services = {
        "Redis": ("localhost", int(os.getenv("REDIS_PORT", "6379"))),
        "Qdrant": ("localhost", int(os.getenv("QDRANT_PORT", "6333"))),
        "MinIO": ("localhost", int(os.getenv("MINIO_ENDPOINT", "localhost:9000").split(":")[1])),
        "MLflow": ("localhost", 5000),
    }

    unavailable = []

    for service_name, (host, port) in services.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()

        if result != 0:
            unavailable.append(f"{service_name} ({host}:{port})")
        else:
            print(f"✅ {service_name} is running on {host}:{port}")

    if unavailable:
        pytest.fail(
            f"❌ Docker services not available: {', '.join(unavailable)}\n"
            f"Please start services with: docker-compose up -d"
        )

    yield


@pytest.fixture(autouse=True, scope="session")
def verify_docker_services(docker_services_running):
    """
    Auto-used session fixture to ensure Docker services are running.
    """
    pass
