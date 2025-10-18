"""
Enterprise message bus implementation with resilience patterns
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import TypeVar

from celery import Celery

from .interfaces import (
    IDeadLetterQueue,
    IEvent,
    IEventHandler,
    IMessage,
    IMessageCommand,
    IMessageCommandHandler,
    IMessageRetryPolicy,
    IMessageSerializer,
    IMessageTracing,
    IMessageValidator,
)

TMessage = TypeVar("TMessage", bound=IMessage)

logger = logging.getLogger(__name__)


class IMessageBus(ABC):
    """Enterprise message bus interface with resilience patterns"""

    @abstractmethod
    async def publish_event(self, event: IEvent) -> None:
        """Publish an event to all interested consumers"""
        pass

    @abstractmethod
    async def send_command(self, command: IMessageCommand) -> None:
        """Send a command to a specific handler"""
        pass

    @abstractmethod
    def register_event_handler(self, event_type: type[IEvent], handler: IEventHandler) -> None:
        """Register an event handler"""
        pass

    @abstractmethod
    def register_command_handler(
        self, command_type: type[IMessageCommand], handler: IMessageCommandHandler
    ) -> None:
        """Register a command handler"""
        pass


class ExponentialBackoffRetryPolicy(IMessageRetryPolicy):
    """Exponential backoff retry policy with jitter"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Retry on most exceptions, but not on validation errors"""
        if attempt >= self.max_retries:
            return False

        # Don't retry validation or permission errors
        if isinstance(error, ValueError | PermissionError):
            return False

        return True

    def get_retry_delay(self, attempt: int) -> float:
        """Exponential backoff with jitter"""
        import random

        delay = min(self.base_delay * (2**attempt), self.max_delay)
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0.1, 0.3) * delay
        return delay + jitter

    def get_max_retries(self) -> int:
        return self.max_retries


class JsonMessageSerializer(IMessageSerializer):
    """JSON serializer for messages"""

    def serialize(self, message: IMessage) -> str:
        """Serialize message to JSON"""
        return message.model_dump_json()

    def deserialize(self, data: str, message_type: type[IMessage]) -> IMessage:
        """Deserialize JSON to message"""
        message_data = json.loads(data)
        return message_type.model_validate(message_data)


class EnterpriseMessageBus(IMessageBus):
    """Enterprise-grade message bus with resilience patterns"""

    def __init__(
        self,
        celery_app: Celery,
        serializer: IMessageSerializer | None = None,
        validator: IMessageValidator | None = None,
        dead_letter_queue: IDeadLetterQueue | None = None,
        retry_policy: IMessageRetryPolicy | None = None,
        tracer: IMessageTracing | None = None,
    ):
        self.celery_app = celery_app
        self.serializer = serializer or JsonMessageSerializer()
        self.validator = validator
        self.dead_letter_queue = dead_letter_queue
        self.retry_policy = retry_policy or ExponentialBackoffRetryPolicy()
        self.tracer = tracer

        self._event_handlers: dict[str, list[IEventHandler]] = {}
        self._command_handlers: dict[str, IMessageCommandHandler] = {}
        self._event_tasks: dict[str, list[str]] = {}
        self._command_tasks: dict[str, str] = {}

    def register_event_handler(self, event_type: type[IEvent], handler: IEventHandler) -> None:
        """Register an event handler"""
        event_name = event_type.__name__
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)
        logger.info(f"Registered event handler: {event_name} -> {handler.__class__.__name__}")

    def register_command_handler(
        self, command_type: type[IMessageCommand], handler: IMessageCommandHandler
    ) -> None:
        """Register a command handler"""
        command_name = command_type.__name__
        if command_name in self._command_handlers:
            logger.warning(f"Overriding existing handler for command: {command_name}")
        self._command_handlers[command_name] = handler
        logger.info(f"Registered command handler: {command_name} -> {handler.__class__.__name__}")

    def register_event_task(self, event_type: type[IEvent], task_name: str) -> None:
        """Register a Celery task to handle a specific event type"""
        event_name = event_type.__name__
        if event_name not in self._event_tasks:
            self._event_tasks[event_name] = []
        self._event_tasks[event_name].append(task_name)
        logger.info(f"Registered event task: {event_name} -> {task_name}")

    def register_command_task(self, command_type: type[IMessageCommand], task_name: str) -> None:
        """Register a Celery task to handle a specific command type"""
        command_name = command_type.__name__
        self._command_tasks[command_name] = task_name
        logger.info(f"Registered command task: {command_name} -> {task_name}")

    async def publish_event(self, event: IEvent) -> None:
        """Publish an event with validation and tracing"""
        event_name = type(event).__name__

        try:
            # Validate event if validator is configured
            if self.validator:
                errors = await self.validator.validate(event)
                if errors:
                    raise ValueError(f"Event validation failed: {errors}")

            # Trace message sent
            if self.tracer:
                await self.tracer.trace_message_sent(event, "event_bus")

            # Send to in-process handlers
            handlers = self._event_handlers.get(event_name, [])
            for handler in handlers:
                try:
                    await handler.handle(event)
                except Exception as e:
                    logger.error(
                        f"In-process event handler failed: {handler.__class__.__name__}: {e}"
                    )
                    await self._handle_message_failure(event, e, handler.__class__.__name__)

            # Send to Celery tasks
            event_data = self.serializer.serialize(event)
            tasks = self._event_tasks.get(event_name, [])

            for task_name in tasks:
                try:
                    self.celery_app.send_task(
                        task_name, args=[event_data], kwargs={"event_type": event_name}
                    )
                    logger.info(f"Published event {event_name} to task {task_name}")
                except Exception as e:
                    logger.error(f"Failed to publish event {event_name} to task {task_name}: {e}")
                    await self._handle_message_failure(event, e, task_name)

        except Exception as e:
            logger.error(f"Failed to publish event {event_name}: {e}")
            await self._handle_message_failure(event, e, "publish_event")
            raise

    async def send_command(self, command: IMessageCommand) -> None:
        """Send a command with validation and retry logic"""
        command_name = type(command).__name__

        try:
            # Validate command if validator is configured
            if self.validator:
                errors = await self.validator.validate(command)
                if errors:
                    raise ValueError(f"Command validation failed: {errors}")

            # Trace message sent
            if self.tracer:
                await self.tracer.trace_message_sent(command, "command_bus")

            # Send to in-process handler first
            handler = self._command_handlers.get(command_name)
            if handler:
                try:
                    await handler.handle(command)
                    return
                except Exception as e:
                    logger.error(
                        f"In-process command handler failed: {handler.__class__.__name__}: {e}"
                    )
                    await self._handle_message_failure(command, e, handler.__class__.__name__)
                    # Fall through to Celery task

            # Send to Celery task
            task_name = self._command_tasks.get(command_name)
            if not task_name:
                raise ValueError(f"No handler registered for command: {command_name}")

            command_data = self.serializer.serialize(command)
            self.celery_app.send_task(
                task_name, args=[command_data], kwargs={"command_type": command_name}
            )
            logger.info(f"Sent command {command_name} to task {task_name}")

        except Exception as e:
            logger.error(f"Failed to send command {command_name}: {e}")
            await self._handle_message_failure(command, e, "send_command")
            raise

    async def _handle_message_failure(
        self, message: IMessage, error: Exception, handler_name: str
    ) -> None:
        """Handle message processing failure with retry logic and DLQ"""
        try:
            # Trace failure
            if self.tracer:
                await self.tracer.trace_message_failed(message, error, handler_name)

            # Send to dead letter queue if configured
            if self.dead_letter_queue:
                retry_count = getattr(message.metadata, "retry_count", 0)
                await self.dead_letter_queue.send_to_dlq(
                    message, error, retry_count, {"handler": handler_name}
                )

        except Exception as dlq_error:
            logger.error(f"Failed to handle message failure: {dlq_error}")


# Legacy CeleryMessageBus for backward compatibility
class CeleryMessageBus(IMessageBus):
    """Legacy message bus - use EnterpriseMessageBus for new code"""

    def __init__(self, celery_app: Celery):
        logger.warning("CeleryMessageBus is deprecated, use EnterpriseMessageBus")
        self.celery_app = celery_app
        self._event_handlers: dict[str, list] = {}
        self._command_handlers: dict[str, str] = {}

    def register_event_handler(self, event_type: type[IEvent], task_name: str) -> None:
        """Register a Celery task to handle a specific event type"""
        event_name = event_type.__name__
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(task_name)
        logger.info(f"Registered event handler: {event_name} -> {task_name}")

    def register_command_handler(self, command_type: type[IMessageCommand], task_name: str) -> None:
        """Register a Celery task to handle a specific command type"""
        command_name = command_type.__name__
        self._command_handlers[command_name] = task_name
        logger.info(f"Registered command handler: {command_name} -> {task_name}")

    async def publish_event(self, event: IEvent) -> None:
        """Publish an event to all registered handlers"""
        event_name = type(event).__name__
        event_data = event.model_dump_json()

        handlers = self._event_handlers.get(event_name, [])

        for task_name in handlers:
            try:
                self.celery_app.send_task(
                    task_name, args=[event_data], kwargs={"event_type": event_name}
                )
                logger.info(f"Published event {event_name} to {task_name}")
            except Exception as e:
                logger.error(f"Failed to publish event {event_name} to {task_name}: {e}")

    async def send_command(self, command: IMessageCommand) -> None:
        """Send a command to its registered handler"""
        command_name = type(command).__name__
        command_data = command.model_dump_json()

        task_name = self._command_handlers.get(command_name)

        if not task_name:
            raise ValueError(f"No handler registered for command: {command_name}")

        try:
            self.celery_app.send_task(
                task_name, args=[command_data], kwargs={"command_type": command_name}
            )
            logger.info(f"Sent command {command_name} to {task_name}")
        except Exception as e:
            logger.error(f"Failed to send command {command_name}: {e}")
            raise

        if not task_name:
            raise ValueError(f"No handler registered for command: {command_name}")

        try:
            # Send to Celery task
            self.celery_app.send_task(
                task_name, args=[command_data], kwargs={"command_type": command_name}
            )
            logger.info(f"Sent command {command_name} to {task_name}")
        except Exception as e:
            logger.error(f"Failed to send command {command_name}: {e}")
            raise


# Global message bus instance
_message_bus: IMessageBus = None


def get_message_bus() -> IMessageBus:
    """Get the global message bus instance"""
    global _message_bus
    if _message_bus is None:
        raise RuntimeError("Message bus not configured. Call configure_message_bus() first.")
    return _message_bus


def configure_message_bus(
    celery_app: Celery, use_enterprise: bool = True, **enterprise_options
) -> IMessageBus:
    """Configure the global message bus with Celery app"""
    global _message_bus
    if use_enterprise:
        _message_bus = EnterpriseMessageBus(celery_app, **enterprise_options)
    else:
        _message_bus = CeleryMessageBus(celery_app)
    return _message_bus


# Utility functions for message handling
def serialize_message(message: IMessage) -> str:
    """Serialize a message to JSON"""
    return message.model_dump_json()


def deserialize_message(message_data: str, message_type: type[TMessage]) -> TMessage:
    """Deserialize JSON to a message object"""
    data = json.loads(message_data)
    return message_type.model_validate(data)
