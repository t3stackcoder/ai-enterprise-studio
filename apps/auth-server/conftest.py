"""
Pytest configuration and fixtures for auth-server tests
"""

import sys
from pathlib import Path

# Add libs to path FIRST
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

import os
from dotenv import load_dotenv

# Load environment variables from project root BEFORE any other imports
env_path = project_root / ".env"
load_dotenv(env_path)

# Set test environment
os.environ["TESTING"] = "true"

# NOW import the rest
import contextlib
import pytest
from database import Base, get_db
from fastapi.testclient import TestClient
from models.user import User
from server import app
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import UTC


@pytest.fixture(scope="session")
def test_engine():
    """
    Create in-memory SQLite database engine for the entire test session.
    This is the parent-level fixture that only manages the database lifecycle.
    Table creation is handled by module-specific fixtures.
    """
    # Create in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Keep connection alive for in-memory DB
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    yield engine

    # Cleanup: dispose engine after all tests
    engine.dispose()


@pytest.fixture(scope="session")
def TestSessionLocal(test_engine):
    """
    Create a session factory bound to the test engine.
    """
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_auth_tables(test_engine):
    """
    Auth module fixture: Create auth-related tables at session start.
    This runs once per test session for the auth module.
    """
    # Create all tables for auth module
    Base.metadata.create_all(bind=test_engine)

    yield

    # Drop tables at end of session
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db_session(test_engine, TestSessionLocal, setup_auth_tables):
    """
    Create a new database session for each test function.
    Truncates all tables after each test for isolation.
    """
    session = TestSessionLocal()

    yield session

    # Truncate all tables after test
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()

    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """
    Create a test client with database session override.
    Each test gets a fresh client with its own DB session.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Disable lifespan to prevent startup/shutdown events from running
    # This prevents init_db() from trying to connect to production PostgreSQL
    original_router = app.router
    app.router.lifespan_context = lambda app: contextlib.nullcontext()

    test_client = TestClient(app, raise_server_exceptions=True)
    yield test_client
    test_client.close()

    # Restore original router
    app.router = original_router
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def sample_user(db_session) -> User:
    """
    Create a sample user for testing.
    Uses credentials from environment variables.
    """
    from datetime import datetime

    import bcrypt

    username = os.getenv("TEST_USER_USERNAME", "testuser")
    password = os.getenv("TEST_USER_PASSWORD", "password123")
    email = os.getenv("TEST_USER_EMAIL", "test@example.com")
    first_name = os.getenv("TEST_USER_FIRST_NAME", "Test")
    last_name = os.getenv("TEST_USER_LAST_NAME", "User")

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    user = User(
        username=username,
        password_hash=password_hash,
        email_address=email,
        first_name=first_name,
        last_name=last_name,
        role="user",
        subscription_tier="free",
        created_at=datetime.now(UTC),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.fixture(scope="function")
def admin_user(db_session) -> User:
    """
    Create an admin user for RBAC testing.
    Uses credentials from environment variables.
    """
    from datetime import datetime

    import bcrypt

    username = os.getenv("TEST_ADMIN_USERNAME", "adminuser")
    password = os.getenv("TEST_ADMIN_PASSWORD", "admin123")
    email = os.getenv("TEST_ADMIN_EMAIL", "admin@example.com")
    first_name = os.getenv("TEST_ADMIN_FIRST_NAME", "Admin")
    last_name = os.getenv("TEST_ADMIN_LAST_NAME", "User")

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    user = User(
        username=username,
        password_hash=password_hash,
        email_address=email,
        first_name=first_name,
        last_name=last_name,
        role="admin",
        subscription_tier="enterprise",
        created_at=datetime.now(UTC),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.fixture(scope="function")
def enterprise_user(db_session) -> User:
    """
    Create an enterprise user for RBAC testing.
    Uses credentials from environment variables.
    """
    from datetime import datetime

    import bcrypt

    username = os.getenv("TEST_ENTERPRISE_USERNAME", "enterpriseuser")
    password = os.getenv("TEST_ENTERPRISE_PASSWORD", "enterprise123")
    email = os.getenv("TEST_ENTERPRISE_EMAIL", "enterprise@example.com")
    first_name = os.getenv("TEST_ENTERPRISE_FIRST_NAME", "Enterprise")
    last_name = os.getenv("TEST_ENTERPRISE_LAST_NAME", "User")

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    user = User(
        username=username,
        password_hash=password_hash,
        email_address=email,
        first_name=first_name,
        last_name=last_name,
        role="enterprise",
        subscription_tier="enterprise",
        created_at=datetime.now(UTC),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.fixture(scope="function")
def authenticated_client(db_session, sample_user):
    """
    Create a test client with an authenticated user.
    Returns tuple of (client, access_token, user)
    """
    username = os.getenv("TEST_USER_USERNAME", "testuser")
    password = os.getenv("TEST_USER_PASSWORD", "password123")

    # Create override
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Disable lifespan
    app.router.lifespan_context = lambda app: contextlib.nullcontext()

    client = TestClient(app, raise_server_exceptions=False)

    # Login to get access token
    response = client.post("/api/auth/login", json={"username": username, "password": password})

    assert response.status_code == 200
    token_data = response.json()
    access_token = token_data["access_token"]

    # Yield client and token
    yield client, access_token, sample_user

    # Cleanup
    client.close()
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def authenticated_admin_client(db_session, admin_user):
    """
    Create a test client with an authenticated admin user.
    Returns tuple of (client, access_token, user)
    """
    username = os.getenv("TEST_ADMIN_USERNAME", "adminuser")
    password = os.getenv("TEST_ADMIN_PASSWORD", "admin123")

    # Create override
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Disable lifespan
    app.router.lifespan_context = lambda app: contextlib.nullcontext()

    client = TestClient(app)

    # Login to get access token
    response = client.post("/api/auth/login", json={"username": username, "password": password})

    assert response.status_code == 200
    token_data = response.json()
    access_token = token_data["access_token"]

    # Yield client and token
    yield client, access_token, admin_user

    # Cleanup
    client.close()
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def authenticated_enterprise_client(db_session, enterprise_user):
    """
    Create a test client with an authenticated enterprise user.
    Returns tuple of (client, access_token, user)
    """
    username = os.getenv("TEST_ENTERPRISE_USERNAME", "enterpriseuser")
    password = os.getenv("TEST_ENTERPRISE_PASSWORD", "enterprise123")

    # Create override
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Disable lifespan
    app.router.lifespan_context = lambda app: contextlib.nullcontext()

    client = TestClient(app)

    # Login to get access token
    response = client.post("/api/auth/login", json={"username": username, "password": password})

    assert response.status_code == 200
    token_data = response.json()
    access_token = token_data["access_token"]

    # Yield client and token
    yield client, access_token, enterprise_user

    # Cleanup
    client.close()
    app.dependency_overrides.clear()
