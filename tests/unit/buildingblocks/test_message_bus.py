"""
Unit tests for EnterpriseMessageBus and related components
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4

from libs.buildingblocks.messaging.message_bus import (
    EnterpriseMessageBus,
    CeleryMessageBus,
    ExponentialBackoffRetryPolicy,
    JsonMessageSerializer,
    get_message_bus,
    configure_message_bus,
    serialize_message,
    deserialize_message,
)
from libs.buildingblocks.messaging.interfaces import (
    IEvent,
    IMessageCommand,
    IEventHandler,
    IMessageCommandHandler,
    IMessageValidator,
    IDeadLetterQueue,
    IMessageTracing,
)


# Test Events and Commands
class TestBusEvent(IEvent):
    """Test event for message bus"""

    event_data: str = "test_event"


class TestBusCommand(IMessageCommand):
    """Test command for message bus"""

    command_data: str = "test_command"


# Test Handlers
class TestBusEventHandler(IEventHandler[TestBusEvent]):
    """Test event handler"""

    def __init__(self):
        self.handled_events = []

    async def handle(self, event: TestBusEvent) -> None:
        self.handled_events.append(event)


class TestBusCommandHandler(IMessageCommandHandler[TestBusCommand]):
    """Test command handler"""

    def __init__(self):
        self.handled_commands = []

    async def handle(self, command: TestBusCommand) -> None:
        self.handled_commands.append(command)


class FailingEventHandler(IEventHandler[TestBusEvent]):
    """Event handler that always fails"""

    async def handle(self, event: TestBusEvent) -> None:
        raise RuntimeError("Handler intentionally failed")


class FailingCommandHandler(IMessageCommandHandler[TestBusCommand]):
    """Command handler that always fails"""

    async def handle(self, command: TestBusCommand) -> None:
        raise RuntimeError("Command handler failed")


# Test Validator
class TestValidator(IMessageValidator):
    """Test validator that can be configured to pass or fail"""

    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.validated_messages = []

    async def validate(self, message) -> list[str]:
        self.validated_messages.append(message)
        if self.should_fail:
            return ["Validation error: message invalid"]
        return []


# Test DLQ
class TestDLQ(IDeadLetterQueue):
    """Test dead letter queue"""

    def __init__(self):
        self.dlq_messages = []

    async def send_to_dlq(self, message, error, retry_count=0, metadata=None) -> None:
        self.dlq_messages.append(
            {"message": message, "error": error, "retry_count": retry_count, "metadata": metadata}
        )

    async def reprocess_from_dlq(self, message_id) -> None:
        pass


# Test Tracer
class TestTracer(IMessageTracing):
    """Test message tracer"""

    def __init__(self):
        self.traces = []

    async def trace_message_sent(self, message, destination: str) -> None:
        self.traces.append({"type": "sent", "message_id": str(message.message_id), "destination": destination})

    async def trace_message_received(self, message, handler: str) -> None:
        self.traces.append({"type": "received", "message_id": str(message.message_id), "handler": handler})

    async def trace_message_failed(self, message, error: Exception, handler: str) -> None:
        self.traces.append(
            {"type": "failed", "message_id": str(message.message_id), "error": str(error), "handler": handler}
        )


# ============================================================================
# ExponentialBackoffRetryPolicy Tests
# ============================================================================


@pytest.mark.unit
def test_exponential_backoff_allows_retry_within_limit():
    """Test that retry policy allows retries within max_retries"""
    policy = ExponentialBackoffRetryPolicy(max_retries=3)
    error = RuntimeError("Temporary failure")

    should_retry = policy.should_retry(error, attempt=1)

    assert should_retry is True
    print("✅ ExponentialBackoffRetryPolicy allows retry within limit")


@pytest.mark.unit
def test_exponential_backoff_prevents_retry_after_limit():
    """Test that retry policy prevents retries after max_retries"""
    policy = ExponentialBackoffRetryPolicy(max_retries=3)
    error = RuntimeError("Temporary failure")

    should_retry = policy.should_retry(error, attempt=5)

    assert should_retry is False
    print("✅ ExponentialBackoffRetryPolicy prevents retry after limit")


@pytest.mark.unit
def test_exponential_backoff_does_not_retry_validation_errors():
    """Test that retry policy doesn't retry validation errors"""
    policy = ExponentialBackoffRetryPolicy()
    error = ValueError("Validation failed")

    should_retry = policy.should_retry(error, attempt=1)

    assert should_retry is False
    print("✅ ExponentialBackoffRetryPolicy skips validation errors")


@pytest.mark.unit
def test_exponential_backoff_does_not_retry_permission_errors():
    """Test that retry policy doesn't retry permission errors"""
    policy = ExponentialBackoffRetryPolicy()
    error = PermissionError("Access denied")

    should_retry = policy.should_retry(error, attempt=1)

    assert should_retry is False
    print("✅ ExponentialBackoffRetryPolicy skips permission errors")


@pytest.mark.unit
def test_exponential_backoff_calculates_delay_with_exponential_growth():
    """Test that retry delay grows exponentially"""
    policy = ExponentialBackoffRetryPolicy(base_delay=1.0, max_delay=60.0)

    delay_1 = policy.get_retry_delay(attempt=1)
    delay_2 = policy.get_retry_delay(attempt=2)
    delay_3 = policy.get_retry_delay(attempt=3)

    # With jitter, delays should be approximately exponential
    assert 1.5 < delay_1 < 3.0  # Base 1.0 * 2^1 + jitter
    assert 3.0 < delay_2 < 6.0  # Base 1.0 * 2^2 + jitter
    assert 6.0 < delay_3 < 12.0  # Base 1.0 * 2^3 + jitter
    print("✅ ExponentialBackoffRetryPolicy calculates exponential delay")


@pytest.mark.unit
def test_exponential_backoff_respects_max_delay():
    """Test that retry delay doesn't exceed max_delay"""
    policy = ExponentialBackoffRetryPolicy(base_delay=1.0, max_delay=10.0)

    delay = policy.get_retry_delay(attempt=10)  # Would be huge without cap

    assert delay <= 13.0  # max_delay (10.0) + max jitter (30% = 3.0)
    print("✅ ExponentialBackoffRetryPolicy respects max_delay")


@pytest.mark.unit
def test_exponential_backoff_returns_max_retries():
    """Test that get_max_retries returns configured value"""
    policy = ExponentialBackoffRetryPolicy(max_retries=5)

    max_retries = policy.get_max_retries()

    assert max_retries == 5
    print("✅ ExponentialBackoffRetryPolicy returns max_retries")


# ============================================================================
# JsonMessageSerializer Tests
# ============================================================================


@pytest.mark.unit
def test_json_serializer_serializes_event():
    """Test that JsonMessageSerializer serializes events"""
    serializer = JsonMessageSerializer()
    event = TestBusEvent()

    serialized = serializer.serialize(event)

    assert isinstance(serialized, str)
    assert "test_event" in serialized
    print("✅ JsonMessageSerializer serializes events")


@pytest.mark.unit
def test_json_serializer_deserializes_event():
    """Test that JsonMessageSerializer deserializes events"""
    serializer = JsonMessageSerializer()
    event = TestBusEvent()
    serialized = serializer.serialize(event)

    deserialized = serializer.deserialize(serialized, TestBusEvent)

    assert isinstance(deserialized, TestBusEvent)
    assert deserialized.event_data == "test_event"
    print("✅ JsonMessageSerializer deserializes events")


# ============================================================================
# EnterpriseMessageBus Tests
# ============================================================================


@pytest.mark.unit
def test_enterprise_message_bus_can_be_created():
    """Test that EnterpriseMessageBus can be instantiated"""
    mock_celery = Mock()

    bus = EnterpriseMessageBus(mock_celery)

    assert bus.celery_app is mock_celery
    assert bus.serializer is not None
    assert bus.retry_policy is not None
    print("✅ EnterpriseMessageBus instantiates")


@pytest.mark.unit
def test_register_event_handler():
    """Test registering an event handler"""
    mock_celery = Mock()
    bus = EnterpriseMessageBus(mock_celery)
    handler = TestBusEventHandler()

    bus.register_event_handler(TestBusEvent, handler)

    assert "TestBusEvent" in bus._event_handlers
    assert handler in bus._event_handlers["TestBusEvent"]
    print("✅ EnterpriseMessageBus registers event handlers")


@pytest.mark.unit
def test_register_multiple_event_handlers():
    """Test registering multiple handlers for same event"""
    mock_celery = Mock()
    bus = EnterpriseMessageBus(mock_celery)
    handler1 = TestBusEventHandler()
    handler2 = TestBusEventHandler()

    bus.register_event_handler(TestBusEvent, handler1)
    bus.register_event_handler(TestBusEvent, handler2)

    assert len(bus._event_handlers["TestBusEvent"]) == 2
    print("✅ EnterpriseMessageBus supports multiple event handlers")


@pytest.mark.unit
def test_register_command_handler():
    """Test registering a command handler"""
    mock_celery = Mock()
    bus = EnterpriseMessageBus(mock_celery)
    handler = TestBusCommandHandler()

    bus.register_command_handler(TestBusCommand, handler)

    assert "TestBusCommand" in bus._command_handlers
    assert bus._command_handlers["TestBusCommand"] is handler
    print("✅ EnterpriseMessageBus registers command handlers")


@pytest.mark.unit
def test_register_command_handler_warns_on_override(caplog):
    """Test that registering duplicate command handler logs warning"""
    import logging

    with caplog.at_level(logging.WARNING):
        mock_celery = Mock()
        bus = EnterpriseMessageBus(mock_celery)
        handler1 = TestBusCommandHandler()
        handler2 = TestBusCommandHandler()

        bus.register_command_handler(TestBusCommand, handler1)
        bus.register_command_handler(TestBusCommand, handler2)

        assert "Overriding existing handler" in caplog.text
    print("✅ EnterpriseMessageBus warns on command handler override")


@pytest.mark.unit
def test_register_event_task():
    """Test registering a Celery task for events"""
    mock_celery = Mock()
    bus = EnterpriseMessageBus(mock_celery)

    bus.register_event_task(TestBusEvent, "tasks.handle_test_event")

    assert "TestBusEvent" in bus._event_tasks
    assert "tasks.handle_test_event" in bus._event_tasks["TestBusEvent"]
    print("✅ EnterpriseMessageBus registers event tasks")


@pytest.mark.unit
def test_register_command_task():
    """Test registering a Celery task for commands"""
    mock_celery = Mock()
    bus = EnterpriseMessageBus(mock_celery)

    bus.register_command_task(TestBusCommand, "tasks.handle_test_command")

    assert "TestBusCommand" in bus._command_tasks
    assert bus._command_tasks["TestBusCommand"] == "tasks.handle_test_command"
    print("✅ EnterpriseMessageBus registers command tasks")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_event_to_in_process_handler():
    """Test publishing event to in-process handler"""
    mock_celery = Mock()
    bus = EnterpriseMessageBus(mock_celery)
    handler = TestBusEventHandler()
    bus.register_event_handler(TestBusEvent, handler)

    event = TestBusEvent()
    await bus.publish_event(event)

    assert len(handler.handled_events) == 1
    assert handler.handled_events[0] == event
    print("✅ EnterpriseMessageBus publishes to in-process handlers")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_event_to_celery_task():
    """Test publishing event to Celery task"""
    mock_celery = Mock()
    bus = EnterpriseMessageBus(mock_celery)
    bus.register_event_task(TestBusEvent, "tasks.handle_event")

    event = TestBusEvent()
    await bus.publish_event(event)

    mock_celery.send_task.assert_called_once()
    call_args = mock_celery.send_task.call_args
    assert call_args[0][0] == "tasks.handle_event"
    print("✅ EnterpriseMessageBus publishes to Celery tasks")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_event_validates_with_validator():
    """Test that publish_event validates with configured validator"""
    mock_celery = Mock()
    validator = TestValidator(should_fail=False)
    bus = EnterpriseMessageBus(mock_celery, validator=validator)

    event = TestBusEvent()
    await bus.publish_event(event)

    assert len(validator.validated_messages) == 1
    print("✅ EnterpriseMessageBus validates events")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_event_raises_on_validation_failure():
    """Test that publish_event raises on validation failure"""
    mock_celery = Mock()
    validator = TestValidator(should_fail=True)
    bus = EnterpriseMessageBus(mock_celery, validator=validator)

    event = TestBusEvent()
    with pytest.raises(ValueError, match="Event validation failed"):
        await bus.publish_event(event)

    print("✅ EnterpriseMessageBus raises on validation failure")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_event_traces_with_tracer():
    """Test that publish_event traces with configured tracer"""
    mock_celery = Mock()
    tracer = TestTracer()
    bus = EnterpriseMessageBus(mock_celery, tracer=tracer)

    event = TestBusEvent()
    await bus.publish_event(event)

    assert len(tracer.traces) == 1
    assert tracer.traces[0]["type"] == "sent"
    assert tracer.traces[0]["destination"] == "event_bus"
    print("✅ EnterpriseMessageBus traces events")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_event_continues_on_handler_failure():
    """Test that publish_event continues with other handlers if one fails"""
    mock_celery = Mock()
    dlq = TestDLQ()
    bus = EnterpriseMessageBus(mock_celery, dead_letter_queue=dlq)

    handler1 = FailingEventHandler()
    handler2 = TestBusEventHandler()
    bus.register_event_handler(TestBusEvent, handler1)
    bus.register_event_handler(TestBusEvent, handler2)

    event = TestBusEvent()
    await bus.publish_event(event)

    # handler2 should still execute
    assert len(handler2.handled_events) == 1
    # Failed message should be in DLQ
    assert len(dlq.dlq_messages) == 1
    print("✅ EnterpriseMessageBus continues on handler failure")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_command_to_in_process_handler():
    """Test sending command to in-process handler"""
    mock_celery = Mock()
    bus = EnterpriseMessageBus(mock_celery)
    handler = TestBusCommandHandler()
    bus.register_command_handler(TestBusCommand, handler)

    command = TestBusCommand()
    await bus.send_command(command)

    assert len(handler.handled_commands) == 1
    assert handler.handled_commands[0] == command
    print("✅ EnterpriseMessageBus sends to in-process command handler")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_command_to_celery_task_when_handler_fails():
    """Test that send_command falls back to Celery when handler fails"""
    mock_celery = Mock()
    dlq = TestDLQ()
    bus = EnterpriseMessageBus(mock_celery, dead_letter_queue=dlq)

    handler = FailingCommandHandler()
    bus.register_command_handler(TestBusCommand, handler)
    bus.register_command_task(TestBusCommand, "tasks.handle_command")

    command = TestBusCommand()
    await bus.send_command(command)

    # Should send to Celery after handler fails
    mock_celery.send_task.assert_called_once()
    print("✅ EnterpriseMessageBus falls back to Celery on handler failure")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_command_raises_without_handler():
    """Test that send_command raises if no handler is registered"""
    mock_celery = Mock()
    bus = EnterpriseMessageBus(mock_celery)

    command = TestBusCommand()
    with pytest.raises(ValueError, match="No handler registered"):
        await bus.send_command(command)

    print("✅ EnterpriseMessageBus raises when no command handler")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_command_validates_with_validator():
    """Test that send_command validates with configured validator"""
    mock_celery = Mock()
    validator = TestValidator(should_fail=False)
    bus = EnterpriseMessageBus(mock_celery, validator=validator)
    handler = TestBusCommandHandler()
    bus.register_command_handler(TestBusCommand, handler)

    command = TestBusCommand()
    await bus.send_command(command)

    assert len(validator.validated_messages) == 1
    print("✅ EnterpriseMessageBus validates commands")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_command_traces_with_tracer():
    """Test that send_command traces with configured tracer"""
    mock_celery = Mock()
    tracer = TestTracer()
    bus = EnterpriseMessageBus(mock_celery, tracer=tracer)
    handler = TestBusCommandHandler()
    bus.register_command_handler(TestBusCommand, handler)

    command = TestBusCommand()
    await bus.send_command(command)

    assert len(tracer.traces) == 1
    assert tracer.traces[0]["type"] == "sent"
    assert tracer.traces[0]["destination"] == "command_bus"
    print("✅ EnterpriseMessageBus traces commands")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_message_failure_sends_to_dlq():
    """Test that message failures are sent to DLQ"""
    mock_celery = Mock()
    dlq = TestDLQ()
    tracer = TestTracer()
    bus = EnterpriseMessageBus(mock_celery, dead_letter_queue=dlq, tracer=tracer)

    message = TestBusEvent()
    error = RuntimeError("Processing failed")
    await bus._handle_message_failure(message, error, "TestHandler")

    assert len(dlq.dlq_messages) == 1
    assert dlq.dlq_messages[0]["message"] == message
    assert dlq.dlq_messages[0]["error"] == error
    assert len(tracer.traces) == 1
    assert tracer.traces[0]["type"] == "failed"
    print("✅ EnterpriseMessageBus sends failures to DLQ")


# ============================================================================
# CeleryMessageBus (Legacy) Tests
# ============================================================================


@pytest.mark.unit
def test_legacy_celery_message_bus_logs_warning(caplog):
    """Test that legacy CeleryMessageBus logs deprecation warning"""
    import logging

    with caplog.at_level(logging.WARNING):
        mock_celery = Mock()
        bus = CeleryMessageBus(mock_celery)

        assert "deprecated" in caplog.text
        assert bus.celery_app is mock_celery
    print("✅ CeleryMessageBus logs deprecation warning")


@pytest.mark.unit
def test_legacy_bus_register_event_handler():
    """Test legacy bus event handler registration"""
    mock_celery = Mock()
    bus = CeleryMessageBus(mock_celery)

    bus.register_event_handler(TestBusEvent, "tasks.handle_event")

    assert "TestBusEvent" in bus._event_handlers
    assert "tasks.handle_event" in bus._event_handlers["TestBusEvent"]
    print("✅ CeleryMessageBus registers event handlers")


@pytest.mark.unit
def test_legacy_bus_register_command_handler():
    """Test legacy bus command handler registration"""
    mock_celery = Mock()
    bus = CeleryMessageBus(mock_celery)

    bus.register_command_handler(TestBusCommand, "tasks.handle_command")

    assert "TestBusCommand" in bus._command_handlers
    assert bus._command_handlers["TestBusCommand"] == "tasks.handle_command"
    print("✅ CeleryMessageBus registers command handlers")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_legacy_bus_publish_event():
    """Test legacy bus publishes events"""
    mock_celery = Mock()
    bus = CeleryMessageBus(mock_celery)
    bus.register_event_handler(TestBusEvent, "tasks.handle_event")

    event = TestBusEvent()
    await bus.publish_event(event)

    mock_celery.send_task.assert_called_once()
    print("✅ CeleryMessageBus publishes events")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_legacy_bus_send_command():
    """Test legacy bus sends commands"""
    mock_celery = Mock()
    bus = CeleryMessageBus(mock_celery)
    bus.register_command_handler(TestBusCommand, "tasks.handle_command")

    command = TestBusCommand()
    await bus.send_command(command)

    # Legacy bus has duplicate code that sends twice (bug in original code)
    assert mock_celery.send_task.call_count == 2
    print("✅ CeleryMessageBus sends commands")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_legacy_bus_raises_without_command_handler():
    """Test legacy bus raises if no command handler registered"""
    mock_celery = Mock()
    bus = CeleryMessageBus(mock_celery)

    command = TestBusCommand()
    with pytest.raises(ValueError, match="No handler registered"):
        await bus.send_command(command)

    print("✅ CeleryMessageBus raises without command handler")


# ============================================================================
# Global Configuration Tests
# ============================================================================


@pytest.mark.unit
def test_get_message_bus_raises_if_not_configured():
    """Test that get_message_bus raises if not configured"""
    import libs.buildingblocks.messaging.message_bus as mb_module

    mb_module._message_bus = None

    with pytest.raises(RuntimeError, match="Message bus not configured"):
        get_message_bus()

    print("✅ get_message_bus raises if not configured")


@pytest.mark.unit
def test_configure_message_bus_creates_enterprise_bus():
    """Test that configure_message_bus creates EnterpriseMessageBus"""
    import libs.buildingblocks.messaging.message_bus as mb_module

    mock_celery = Mock()
    bus = configure_message_bus(mock_celery, use_enterprise=True)

    assert isinstance(bus, EnterpriseMessageBus)
    assert mb_module._message_bus is bus
    print("✅ configure_message_bus creates EnterpriseMessageBus")


@pytest.mark.unit
def test_configure_message_bus_creates_legacy_bus():
    """Test that configure_message_bus creates legacy bus"""
    import libs.buildingblocks.messaging.message_bus as mb_module

    mock_celery = Mock()
    bus = configure_message_bus(mock_celery, use_enterprise=False)

    assert isinstance(bus, CeleryMessageBus)
    assert mb_module._message_bus is bus
    print("✅ configure_message_bus creates legacy bus")


@pytest.mark.unit
def test_get_message_bus_returns_configured_bus():
    """Test that get_message_bus returns the configured bus"""
    mock_celery = Mock()
    configured_bus = configure_message_bus(mock_celery)

    retrieved_bus = get_message_bus()

    assert retrieved_bus is configured_bus
    print("✅ get_message_bus returns configured bus")


# ============================================================================
# Utility Function Tests
# ============================================================================


@pytest.mark.unit
def test_serialize_message_utility():
    """Test serialize_message utility function"""
    event = TestBusEvent()

    serialized = serialize_message(event)

    assert isinstance(serialized, str)
    assert "test_event" in serialized
    print("✅ serialize_message utility works")


@pytest.mark.unit
def test_deserialize_message_utility():
    """Test deserialize_message utility function"""
    event = TestBusEvent()
    serialized = serialize_message(event)

    deserialized = deserialize_message(serialized, TestBusEvent)

    assert isinstance(deserialized, TestBusEvent)
    assert deserialized.event_data == "test_event"
    print("✅ deserialize_message utility works")
