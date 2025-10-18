"""
Message interfaces for event-driven architecture
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# Type variables for generic handler interfaces
TEvent = TypeVar("TEvent", bound="IEvent")
TCommand = TypeVar("TCommand", bound="IMessageCommand")


class IMessage(BaseModel, ABC):
    """Base interface for all messages"""

    message_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IEvent(IMessage, ABC):
    """Base interface for domain events (something that happened)"""

    pass


class IMessageCommand(IMessage, ABC):
    """Base interface for message commands (something that should happen)"""

    pass


class IIntegrationEvent(IEvent, ABC):
    """Events that cross service boundaries"""

    service_name: str
    version: str
    schema_version: str = "1.0"


# Enterprise messaging interfaces
class IEventHandler(ABC, Generic[TEvent]):
    """Handler for domain events"""

    @abstractmethod
    async def handle(self, event: TEvent) -> None:
        """Handle a domain event"""
        pass


class IMessageCommandHandler(ABC, Generic[TCommand]):
    """Handler for message commands"""

    @abstractmethod
    async def handle(self, command: TCommand) -> None:
        """Handle a message command"""
        pass


class IMessageSerializer(ABC):
    """Serializes and deserializes messages for transport"""

    @abstractmethod
    def serialize(self, message: IMessage) -> str:
        """Serialize message to string for transport"""
        pass

    @abstractmethod
    def deserialize(self, data: str, message_type: type[IMessage]) -> IMessage:
        """Deserialize string data back to message"""
        pass


class IMessageValidator(ABC):
    """Validates message structure and business rules"""

    @abstractmethod
    async def validate(self, message: IMessage) -> list[str]:
        """Validate message, return list of errors (empty if valid)"""
        pass


class IDeadLetterQueue(ABC):
    """Handles failed message processing"""

    @abstractmethod
    async def send_to_dlq(
        self,
        message: IMessage,
        error: Exception,
        retry_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Send failed message to dead letter queue"""
        pass

    @abstractmethod
    async def reprocess_from_dlq(self, message_id: UUID) -> None:
        """Reprocess a message from dead letter queue"""
        pass


class IMessageTracing(ABC):
    """Message observability and distributed tracing"""

    @abstractmethod
    async def trace_message_sent(self, message: IMessage, destination: str) -> None:
        """Record message being sent"""
        pass

    @abstractmethod
    async def trace_message_received(self, message: IMessage, handler: str) -> None:
        """Record message being received and processed"""
        pass

    @abstractmethod
    async def trace_message_failed(self, message: IMessage, error: Exception, handler: str) -> None:
        """Record message processing failure"""
        pass


class IMessageRetryPolicy(ABC):
    """Defines retry behavior for failed messages"""

    @abstractmethod
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if message should be retried"""
        pass

    @abstractmethod
    def get_retry_delay(self, attempt: int) -> float:
        """Get delay before next retry attempt in seconds"""
        pass

    @abstractmethod
    def get_max_retries(self) -> int:
        """Get maximum number of retry attempts"""
        pass
