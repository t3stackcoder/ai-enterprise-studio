"""
Database configuration and session management for auth-server
"""

import os
import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

# Import the Base from models to ensure all models are registered
from models.user import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Get database URL from environment (defaults to SQLite for development)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auth_server.db")

# Create engine
# For SQLite: check_same_thread=False allows multiple threads
# For PostgreSQL: pool settings can be tuned
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL pooling settings
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_pre_ping"] = True  # Verify connections before using

engine = create_engine(DATABASE_URL, **engine_kwargs)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize database - create all tables
    Call this on application startup
    """
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized: {DATABASE_URL}")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get database session

    Usage in endpoints:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions (for non-FastAPI usage)

    Usage:
        with get_db_context() as db:
            users = db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def close_db():
    """
    Close database engine and cleanup
    Call this on application shutdown
    """
    engine.dispose()
    print("Database connections closed")
