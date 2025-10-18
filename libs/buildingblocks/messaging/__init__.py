"""
Enterprise messaging infrastructure for VisionScope
Event-driven architecture with resilience patterns
"""

from .interfaces import (
    IDeadLetterQueue,
    IEvent,
    IEventHandler,
    IIntegrationEvent,
    IMessage,
    IMessageCommand,
    IMessageCommandHandler,
    IMessageRetryPolicy,
    IMessageSerializer,
    IMessageTracing,
    IMessageValidator,
)
from .message_bus import (
    CeleryMessageBus,
    EnterpriseMessageBus,
    ExponentialBackoffRetryPolicy,
    IMessageBus,
    JsonMessageSerializer,
    configure_message_bus,
    deserialize_message,
    get_message_bus,
    serialize_message,
)

# Celery config will be imported when needed to avoid dependency issues

__all__ = [
    # Core Interfaces
    "IMessage",
    "IEvent",
    "IMessageCommand",
    "IIntegrationEvent",
    # Handler Interfaces
    "IEventHandler",
    "IMessageCommandHandler",
    # Infrastructure Interfaces
    "IMessageBus",
    "IMessageSerializer",
    "IMessageValidator",
    "IDeadLetterQueue",
    "IMessageRetryPolicy",
    "IMessageTracing",
    # Implementations
    "EnterpriseMessageBus",
    "CeleryMessageBus",  # Legacy
    "JsonMessageSerializer",
    "ExponentialBackoffRetryPolicy",
    # Utilities
    "get_message_bus",
    "configure_message_bus",
    "serialize_message",
    "deserialize_message",
]
