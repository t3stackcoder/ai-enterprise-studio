"""
User model for VisionScope authentication
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import String as SQLString
from sqlalchemy.types import TypeDecorator


class UUID(TypeDecorator):
    """Platform-independent UUID type that works with SQLite and PostgreSQL"""

    impl = SQLString
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(dialect.UUID())
        else:
            return dialect.type_descriptor(SQLString(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


Base = declarative_base()


class User(Base):
    """Core user entity for VisionScope platform"""

    __tablename__ = "users"

    # Primary identity
    user_id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=True)
    password_hash = Column(Text, nullable=True)
    role = Column(String(50), default="user", nullable=False)  # user, admin, enterprise
    refresh_token = Column(Text, nullable=True)
    refresh_token_expiry_time = Column(DateTime, nullable=True)

    # Personal information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    birthdate = Column(DateTime, nullable=True)

    # Contact information
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state_id = Column(Integer, ForeignKey("states.id"), nullable=True)
    zip_code = Column(String(20), nullable=True)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=True)
    mobile_number = Column(String(20), nullable=True)
    email_address = Column(String(255), unique=True, nullable=True)

    # VisionScope specific
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_login = Column(DateTime, nullable=True)
    subscription_tier = Column(
        String(50), default="free", nullable=False
    )  # free, premium, enterprise

    # Navigation properties (relationships)
    country = relationship("Country", back_populates="users")
    state = relationship("State", back_populates="users")
    # VisionScope specific relationships (commented out until models are created)
    # video_projects = relationship("VideoProject", back_populates="user")
    # usage_analytics = relationship("UsageAnalytics", back_populates="user")


class Country(Base):
    """Country lookup table"""

    __tablename__ = "countries"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    code = Column(String(3), nullable=False)  # ISO code

    # Navigation properties
    users = relationship("User", back_populates="country")


class State(Base):
    """State/Province lookup table"""

    __tablename__ = "states"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    code = Column(String(10), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)

    # Navigation properties
    country = relationship("Country")
    users = relationship("User", back_populates="state")
