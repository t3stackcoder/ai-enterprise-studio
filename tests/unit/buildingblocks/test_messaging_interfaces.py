"""
Unit tests for messaging interfaces and Celery configuration
"""

import pytest
from datetime import datetime
from uuid import UUID, uuid4
from typing import Any

from libs.buildingblocks.messaging.interfaces import (
    IMessage,
    IEvent,
    IMessageCommand,
    IIntegrationEvent,
    IEventHandler,
    IMessageCommandHandler,
    IMessageSerializer,
    IMessageValidator,
    IDeadLetterQueue,
    IMessageTracing,
    IMessageRetryPolicy,
)


# ============================================================================
# Test Message Implementations
# ============================================================================


class TestEvent(IEvent):
    """Test event implementation"""

    event_type: str = "test_event"
    data: str = "test_data"


class TestCommand(IMessageCommand):
    """Test command implementation"""

    command_type: str = "test_command"
    action: str = "test_action"


class TestIntegrationEvent(IIntegrationEvent):
    """Test integration event implementation"""

    service_name: str = "test_service"
    version: str = "1.0.0"
    event_data: dict[str, Any] = {}


# ============================================================================
# Test Handler Implementations
# ============================================================================


class TestEventHandler(IEventHandler[TestEvent]):
    """Test event handler implementation"""

    def __init__(self):
        self.handled_events = []

    async def handle(self, event: TestEvent) -> None:
        self.handled_events.append(event)


class TestCommandHandler(IMessageCommandHandler[TestCommand]):
    """Test command handler implementation"""

    def __init__(self):
        self.handled_commands = []

    async def handle(self, command: TestCommand) -> None:
        self.handled_commands.append(command)


# ============================================================================
# Test Service Implementations
# ============================================================================


class TestMessageSerializer(IMessageSerializer):
    """Test serializer implementation"""

    def serialize(self, message: IMessage) -> str:
        return message.model_dump_json()

    def deserialize(self, data: str, message_type: type[IMessage]) -> IMessage:
        return message_type.model_validate_json(data)


class TestMessageValidator(IMessageValidator):
    """Test validator implementation"""

    async def validate(self, message: IMessage) -> list[str]:
        errors = []
        if not message.message_id:
            errors.append("message_id is required")
        if not message.timestamp:
            errors.append("timestamp is required")
        return errors


class TestDeadLetterQueue(IDeadLetterQueue):
    """Test DLQ implementation"""

    def __init__(self):
        self.dlq_messages = []

    async def send_to_dlq(
        self,
        message: IMessage,
        error: Exception,
        retry_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.dlq_messages.append(
            {"message": message, "error": error, "retry_count": retry_count, "metadata": metadata}
        )

    async def reprocess_from_dlq(self, message_id: UUID) -> None:
        pass


class TestMessageTracing(IMessageTracing):
    """Test tracing implementation"""

    def __init__(self):
        self.traces = []

    async def trace_message_sent(self, message: IMessage, destination: str) -> None:
        self.traces.append({"type": "sent", "message_id": message.message_id, "destination": destination})

    async def trace_message_received(self, message: IMessage, handler: str) -> None:
        self.traces.append({"type": "received", "message_id": message.message_id, "handler": handler})

    async def trace_message_failed(self, message: IMessage, error: Exception, handler: str) -> None:
        self.traces.append(
            {"type": "failed", "message_id": message.message_id, "error": str(error), "handler": handler}
        )


class TestMessageRetryPolicy(IMessageRetryPolicy):
    """Test retry policy implementation"""

    def should_retry(self, error: Exception, attempt: int) -> bool:
        return attempt < 3

    def get_retry_delay(self, attempt: int) -> float:
        return 2.0**attempt  # Exponential backoff

    def get_max_retries(self) -> int:
        return 3


# ============================================================================
# IMessage Tests
# ============================================================================


@pytest.mark.unit
def test_message_has_default_message_id():
    """Test that IMessage generates message_id by default"""
    event = TestEvent()

    assert event.message_id is not None
    assert isinstance(event.message_id, UUID)
    print("✅ IMessage generates message_id")


@pytest.mark.unit
def test_message_has_default_timestamp():
    """Test that IMessage generates timestamp by default"""
    event = TestEvent()

    assert event.timestamp is not None
    assert isinstance(event.timestamp, datetime)
    print("✅ IMessage generates timestamp")


@pytest.mark.unit
def test_message_can_have_correlation_id():
    """Test that IMessage supports correlation_id"""
    correlation_id = uuid4()
    event = TestEvent(correlation_id=correlation_id)

    assert event.correlation_id == correlation_id
    print("✅ IMessage supports correlation_id")


@pytest.mark.unit
def test_message_has_metadata_dict():
    """Test that IMessage has metadata dictionary"""
    metadata = {"user_id": "123", "tenant": "acme"}
    event = TestEvent(metadata=metadata)

    assert event.metadata == metadata
    print("✅ IMessage supports metadata")


# ============================================================================
# IEvent Tests
# ============================================================================


@pytest.mark.unit
def test_event_inherits_from_message():
    """Test that IEvent inherits from IMessage"""
    event = TestEvent()

    assert isinstance(event, IMessage)
    assert hasattr(event, "message_id")
    assert hasattr(event, "timestamp")
    print("✅ IEvent inherits from IMessage")


# ============================================================================
# IMessageCommand Tests
# ============================================================================


@pytest.mark.unit
def test_command_inherits_from_message():
    """Test that IMessageCommand inherits from IMessage"""
    command = TestCommand()

    assert isinstance(command, IMessage)
    assert hasattr(command, "message_id")
    assert hasattr(command, "timestamp")
    print("✅ IMessageCommand inherits from IMessage")


# ============================================================================
# IIntegrationEvent Tests
# ============================================================================


@pytest.mark.unit
def test_integration_event_has_service_info():
    """Test that IIntegrationEvent includes service metadata"""
    event = TestIntegrationEvent()

    assert event.service_name == "test_service"
    assert event.version == "1.0.0"
    assert event.schema_version == "1.0"
    print("✅ IIntegrationEvent has service metadata")


# ============================================================================
# IEventHandler Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_event_handler_can_handle_events():
    """Test that IEventHandler can handle events"""
    handler = TestEventHandler()
    event = TestEvent()

    await handler.handle(event)

    assert len(handler.handled_events) == 1
    assert handler.handled_events[0] == event
    print("✅ IEventHandler handles events")


# ============================================================================
# IMessageCommandHandler Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_command_handler_can_handle_commands():
    """Test that IMessageCommandHandler can handle commands"""
    handler = TestCommandHandler()
    command = TestCommand()

    await handler.handle(command)

    assert len(handler.handled_commands) == 1
    assert handler.handled_commands[0] == command
    print("✅ IMessageCommandHandler handles commands")


# ============================================================================
# IMessageSerializer Tests
# ============================================================================


@pytest.mark.unit
def test_message_serializer_serializes_to_string():
    """Test that IMessageSerializer serializes messages"""
    serializer = TestMessageSerializer()
    event = TestEvent()

    serialized = serializer.serialize(event)

    assert isinstance(serialized, str)
    assert event.event_type in serialized
    print("✅ IMessageSerializer serializes messages")


@pytest.mark.unit
def test_message_serializer_deserializes_from_string():
    """Test that IMessageSerializer deserializes messages"""
    serializer = TestMessageSerializer()
    event = TestEvent()
    serialized = serializer.serialize(event)

    deserialized = serializer.deserialize(serialized, TestEvent)

    assert isinstance(deserialized, TestEvent)
    assert deserialized.event_type == event.event_type
    print("✅ IMessageSerializer deserializes messages")


# ============================================================================
# IMessageValidator Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_message_validator_validates_messages():
    """Test that IMessageValidator validates messages"""
    validator = TestMessageValidator()
    event = TestEvent()

    errors = await validator.validate(event)

    assert isinstance(errors, list)
    assert len(errors) == 0  # No errors for valid message
    print("✅ IMessageValidator validates messages")


# ============================================================================
# IDeadLetterQueue Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dead_letter_queue_accepts_failed_messages():
    """Test that IDeadLetterQueue accepts failed messages"""
    dlq = TestDeadLetterQueue()
    event = TestEvent()
    error = Exception("Processing failed")

    await dlq.send_to_dlq(event, error, retry_count=3, metadata={"reason": "timeout"})

    assert len(dlq.dlq_messages) == 1
    assert dlq.dlq_messages[0]["message"] == event
    assert dlq.dlq_messages[0]["error"] == error
    assert dlq.dlq_messages[0]["retry_count"] == 3
    print("✅ IDeadLetterQueue accepts failed messages")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dead_letter_queue_can_reprocess():
    """Test that IDeadLetterQueue can reprocess messages"""
    dlq = TestDeadLetterQueue()
    message_id = uuid4()

    # Should not raise
    await dlq.reprocess_from_dlq(message_id)
    print("✅ IDeadLetterQueue can reprocess messages")


# ============================================================================
# IMessageTracing Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_message_tracing_traces_sent_messages():
    """Test that IMessageTracing tracks sent messages"""
    tracer = TestMessageTracing()
    event = TestEvent()

    await tracer.trace_message_sent(event, "queue://billing")

    assert len(tracer.traces) == 1
    assert tracer.traces[0]["type"] == "sent"
    assert tracer.traces[0]["destination"] == "queue://billing"
    print("✅ IMessageTracing traces sent messages")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_message_tracing_traces_received_messages():
    """Test that IMessageTracing tracks received messages"""
    tracer = TestMessageTracing()
    event = TestEvent()

    await tracer.trace_message_received(event, "TestEventHandler")

    assert len(tracer.traces) == 1
    assert tracer.traces[0]["type"] == "received"
    assert tracer.traces[0]["handler"] == "TestEventHandler"
    print("✅ IMessageTracing traces received messages")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_message_tracing_traces_failed_messages():
    """Test that IMessageTracing tracks failed messages"""
    tracer = TestMessageTracing()
    event = TestEvent()
    error = Exception("Handler failed")

    await tracer.trace_message_failed(event, error, "TestEventHandler")

    assert len(tracer.traces) == 1
    assert tracer.traces[0]["type"] == "failed"
    assert tracer.traces[0]["handler"] == "TestEventHandler"
    assert "Handler failed" in tracer.traces[0]["error"]
    print("✅ IMessageTracing traces failed messages")


# ============================================================================
# IMessageRetryPolicy Tests
# ============================================================================


@pytest.mark.unit
def test_retry_policy_determines_if_should_retry():
    """Test that IMessageRetryPolicy determines retry eligibility"""
    policy = TestMessageRetryPolicy()
    error = Exception("Temporary failure")

    should_retry_1 = policy.should_retry(error, 1)
    should_retry_5 = policy.should_retry(error, 5)

    assert should_retry_1 is True
    assert should_retry_5 is False
    print("✅ IMessageRetryPolicy determines retry eligibility")


@pytest.mark.unit
def test_retry_policy_calculates_retry_delay():
    """Test that IMessageRetryPolicy calculates retry delay"""
    policy = TestMessageRetryPolicy()

    delay_1 = policy.get_retry_delay(1)
    delay_2 = policy.get_retry_delay(2)

    assert delay_1 == 2.0
    assert delay_2 == 4.0  # Exponential backoff
    print("✅ IMessageRetryPolicy calculates retry delay")


@pytest.mark.unit
def test_retry_policy_has_max_retries():
    """Test that IMessageRetryPolicy defines max retries"""
    policy = TestMessageRetryPolicy()

    max_retries = policy.get_max_retries()

    assert max_retries == 3
    print("✅ IMessageRetryPolicy defines max retries")


# ============================================================================
# Celery Configuration Tests (import-only, no execution)
# ============================================================================


@pytest.mark.unit
def test_celery_config_can_be_imported():
    """Test that celery_config module can be imported"""
    from libs.buildingblocks.messaging import celery_config

    assert hasattr(celery_config, "celery_app")
    assert hasattr(celery_config, "CeleryConfig")
    print("✅ celery_config module imports successfully")


@pytest.mark.unit
def test_celery_config_class_has_expected_attributes():
    """Test that CeleryConfig class has expected configuration"""
    from libs.buildingblocks.messaging.celery_config import CeleryConfig

    assert hasattr(CeleryConfig, "broker_url")
    assert hasattr(CeleryConfig, "result_backend")
    assert hasattr(CeleryConfig, "task_serializer")
    assert hasattr(CeleryConfig, "task_routes")
    assert CeleryConfig.task_serializer == "json"
    assert CeleryConfig.timezone == "UTC"
    print("✅ CeleryConfig has expected attributes")


@pytest.mark.unit
def test_celery_app_is_configured():
    """Test that celery_app is properly configured"""
    from libs.buildingblocks.messaging.celery_config import celery_app

    assert celery_app.main == "visionscope"  # Celery uses .main not .name
    # Don't test actual config values as they depend on environment
    print("✅ celery_app is configured")
