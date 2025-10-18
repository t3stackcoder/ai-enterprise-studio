"""
Event Outbox model for transactional outbox pattern
"""

import json
import uuid
from datetime import datetime
from typing import Any

from models.user import UUID, Base
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func


class EventOutbox(Base):
    """
    Outbox table for storing events before publishing to message bus
    Implements the Transactional Outbox pattern for guaranteed event delivery
    """

    __tablename__ = "event_outbox"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    event_type = Column(String(255), nullable=False)
    event_data = Column(Text, nullable=False)  # JSON-serialized event
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    published_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    correlation_id = Column(UUID, nullable=True)

    def __repr__(self) -> str:
        status = "published" if self.published_at else "pending"
        return f"<EventOutbox(id={self.id}, type={self.event_type}, status={status})>"

    @property
    def is_published(self) -> bool:
        """Check if event has been published"""
        return self.published_at is not None

    @property
    def event_data_dict(self) -> dict[str, Any]:
        """Get event data as dictionary"""
        return json.loads(self.event_data)

    @classmethod
    def from_event(cls, event: Any, correlation_id: uuid.UUID | None = None) -> "EventOutbox":
        """
        Create outbox record from domain event

        Args:
            event: Domain event object (must have model_dump_json() method)
            correlation_id: Optional correlation ID for tracking

        Returns:
            EventOutbox instance ready to save
        """
        return cls(
            event_type=(getattr(event, "event_type", None) or type(event).__name__),
            event_data=(
                event.model_dump_json()
                if hasattr(event, "model_dump_json")
                else json.dumps(event.__dict__)
            ),
            correlation_id=correlation_id,
        )

    def mark_as_published(self) -> None:
        """Mark event as successfully published"""
        self.published_at = datetime.utcnow()

    def mark_as_failed(self, error_message: str) -> None:
        """Mark event as failed and increment retry count"""
        self.retry_count += 1
        self.error_message = error_message

    def reconstruct_event(self, event_class: type) -> Any:
        """
        Reconstruct original event object from stored data

        Args:
            event_class: The event class to reconstruct

        Returns:
            Reconstructed event object
        """
        if hasattr(event_class, "model_validate_json"):
            # Pydantic model
            return event_class.model_validate_json(self.event_data)
        else:
            # Regular class
            data = json.loads(self.event_data)
            return event_class(**data)
