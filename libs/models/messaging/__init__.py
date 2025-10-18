"""
Messaging-related database models

This package contains models related to the enterprise messaging infrastructure,
including the transactional outbox pattern for guaranteed event delivery.
"""

from .event_outbox import EventOutbox

__all__ = [
    "EventOutbox",
]
