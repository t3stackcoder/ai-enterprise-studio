"""
Unit tests for TransactionBehavior and OutboxBehavior
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock

from libs.buildingblocks.behaviors.pipeline_behaviors import (
    TransactionBehavior,
    OutboxBehavior,
)
from libs.buildingblocks.cqrs.interfaces import ICommand, ICommandWithResponse, IQuery
from libs.buildingblocks.exceptions.pipeline_exceptions import TransactionPipelineException


# Mock database session
class MockDBSession:
    def __init__(self):
        self.in_transaction_flag = False
        self.committed = False
        self.rolled_back = False
        self.begun = False

    def in_transaction(self):
        return self.in_transaction_flag

    def begin(self):
        self.begun = True
        self.in_transaction_flag = True

    def commit(self):
        self.committed = True
        self.in_transaction_flag = False

    def rollback(self):
        self.rolled_back = True
        self.in_transaction_flag = False


# Test Commands
class TransactionalCommand(ICommand):
    def __init__(self, db_session=None):
        self.requires_transaction = True
        self.db_session = db_session


class NonTransactionalCommand(ICommand):
    def __init__(self):
        self.requires_transaction = False


class CommandWithoutTransactionFlag(ICommand):
    pass


class CommandWithDomainEvents(ICommand):
    def __init__(self, events=None, db_session=None, correlation_id=None):
        self.domain_events = events or []
        self.db_session = db_session
        self.correlation_id = correlation_id


class QueryWithDomainEvents(IQuery[str]):
    def __init__(self, events=None):
        self.domain_events = events or []


# Helper functions
async def success_handler():
    """Handler that succeeds"""
    return "success"


async def failing_handler():
    """Handler that fails"""
    raise ValueError("Handler failed")


# ============================================================================
# TransactionBehavior Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transaction_behavior_skips_non_transactional_requests():
    """
    Test that TransactionBehavior skips requests that don't require transactions.
    """
    behavior = TransactionBehavior()
    command = NonTransactionalCommand()

    result = await behavior.handle(command, success_handler)

    assert result == "success"
    print("✅ TransactionBehavior skipped non-transactional request")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transaction_behavior_skips_requests_without_flag():
    """
    Test that TransactionBehavior skips requests without requires_transaction attribute.
    """
    behavior = TransactionBehavior()
    command = CommandWithoutTransactionFlag()

    result = await behavior.handle(command, success_handler)

    assert result == "success"
    print("✅ TransactionBehavior skipped request without transaction flag")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transaction_behavior_skips_without_db_session(caplog):
    """
    Test that TransactionBehavior logs warning and continues without db_session.
    """
    import logging

    with caplog.at_level(logging.WARNING):
        behavior = TransactionBehavior()
        command = TransactionalCommand(db_session=None)

        result = await behavior.handle(command, success_handler)

        assert result == "success"
        assert "no db_session found" in caplog.text
    print("✅ TransactionBehavior warned about missing db_session")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transaction_behavior_begins_transaction():
    """
    Test that TransactionBehavior begins transaction if not already started.
    """
    behavior = TransactionBehavior(auto_commit=False)
    db_session = MockDBSession()
    command = TransactionalCommand(db_session=db_session)

    await behavior.handle(command, success_handler)

    assert db_session.begun is True
    assert db_session.in_transaction_flag is True
    print("✅ TransactionBehavior began transaction")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transaction_behavior_skips_begin_if_already_in_transaction():
    """
    Test that TransactionBehavior doesn't begin if already in transaction.
    """
    behavior = TransactionBehavior()
    db_session = MockDBSession()
    db_session.in_transaction_flag = True  # Already in transaction
    command = TransactionalCommand(db_session=db_session)

    await behavior.handle(command, success_handler)

    assert db_session.begun is False  # Should not call begin()
    print("✅ TransactionBehavior skipped begin for existing transaction")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transaction_behavior_auto_commits_on_success():
    """
    Test that TransactionBehavior auto-commits when auto_commit=True.
    """
    behavior = TransactionBehavior(auto_commit=True)
    db_session = MockDBSession()
    command = TransactionalCommand(db_session=db_session)

    result = await behavior.handle(command, success_handler)

    assert result == "success"
    assert db_session.committed is True
    assert db_session.rolled_back is False
    print("✅ TransactionBehavior auto-committed on success")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transaction_behavior_does_not_commit_when_disabled():
    """
    Test that TransactionBehavior doesn't commit when auto_commit=False.
    """
    behavior = TransactionBehavior(auto_commit=False)
    db_session = MockDBSession()
    command = TransactionalCommand(db_session=db_session)

    result = await behavior.handle(command, success_handler)

    assert result == "success"
    assert db_session.committed is False
    print("✅ TransactionBehavior skipped commit when auto_commit=False")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transaction_behavior_rolls_back_on_error():
    """
    Test that TransactionBehavior rolls back transaction on error.
    """
    behavior = TransactionBehavior()
    db_session = MockDBSession()
    command = TransactionalCommand(db_session=db_session)

    with pytest.raises(TransactionPipelineException) as exc_info:
        await behavior.handle(command, failing_handler)

    assert db_session.rolled_back is True
    assert db_session.committed is False
    assert exc_info.value.operation == "rollback"
    print("✅ TransactionBehavior rolled back on error")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_transaction_behavior_preserves_original_exception(caplog):
    """
    Test that TransactionBehavior logs original exception during rollback.
    """
    import logging

    with caplog.at_level(logging.ERROR):
        behavior = TransactionBehavior()
        db_session = MockDBSession()
        command = TransactionalCommand(db_session=db_session)

        with pytest.raises(TransactionPipelineException):
            await behavior.handle(command, failing_handler)

        assert "rolled back" in caplog.text
        assert "Handler failed" in caplog.text
    print("✅ TransactionBehavior logged original exception")


# ============================================================================
# OutboxBehavior Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_outbox_behavior_skips_queries():
    """
    Test that OutboxBehavior skips queries (only processes commands).
    """
    behavior = OutboxBehavior()
    query = QueryWithDomainEvents(events=["event1"])

    result = await behavior.handle(query, success_handler)

    assert result == "success"
    print("✅ OutboxBehavior skipped query")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_outbox_behavior_skips_commands_without_events():
    """
    Test that OutboxBehavior skips commands without domain_events.
    """
    behavior = OutboxBehavior()

    class SimpleCommand(ICommand):
        pass

    command = SimpleCommand()
    result = await behavior.handle(command, success_handler)

    assert result == "success"
    print("✅ OutboxBehavior skipped command without events")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_outbox_behavior_skips_commands_with_empty_events():
    """
    Test that OutboxBehavior skips commands with empty domain_events list.
    """
    behavior = OutboxBehavior()
    command = CommandWithDomainEvents(events=[])

    result = await behavior.handle(command, success_handler)

    assert result == "success"
    print("✅ OutboxBehavior skipped command with empty events")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_outbox_behavior_warns_without_db_session(caplog):
    """
    Test that OutboxBehavior warns when db_session is missing.
    """
    import logging

    with caplog.at_level(logging.WARNING):
        behavior = OutboxBehavior()
        command = CommandWithDomainEvents(events=["event1"], db_session=None)

        result = await behavior.handle(command, success_handler)

        assert result == "success"
        assert "No db_session found" in caplog.text
    print("✅ OutboxBehavior warned about missing db_session")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_outbox_behavior_errors_without_mediator(caplog):
    """
    Test that OutboxBehavior logs error when mediator is not configured.
    """
    import logging

    with caplog.at_level(logging.ERROR):
        behavior = OutboxBehavior(mediator=None)
        db_session = Mock()
        command = CommandWithDomainEvents(events=["event1"], db_session=db_session)

        result = await behavior.handle(command, success_handler)

        assert result == "success"
        assert "No mediator configured" in caplog.text
    print("✅ OutboxBehavior logged error without mediator")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_outbox_behavior_saves_single_event(monkeypatch):
    """
    Test that OutboxBehavior saves single domain event to outbox.
    """
    # Mock the SaveEventToOutboxCommand class
    class MockSaveEventToOutboxCommand:
        def __init__(self, event, correlation_id, db_session):
            self.event = event
            self.correlation_id = correlation_id
            self.db_session = db_session

    # Patch the import to avoid the import error
    import sys
    from unittest.mock import MagicMock

    mock_outbox_module = MagicMock()
    mock_outbox_module.SaveEventToOutboxCommand = MockSaveEventToOutboxCommand
    sys.modules["libs.buildingblocks.messaging.outbox_cqrs"] = mock_outbox_module

    mock_mediator = AsyncMock()
    behavior = OutboxBehavior(mediator=mock_mediator)
    db_session = Mock()
    event = {"type": "UserCreated", "user_id": "123"}
    command = CommandWithDomainEvents(
        events=[event], db_session=db_session, correlation_id="test-123"
    )

    result = await behavior.handle(command, success_handler)

    assert result == "success"
    assert mock_mediator.send_command.called
    call_args = mock_mediator.send_command.call_args[0][0]
    assert hasattr(call_args, "event")
    assert call_args.event == event
    print("✅ OutboxBehavior saved single event")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_outbox_behavior_saves_multiple_events(monkeypatch):
    """
    Test that OutboxBehavior saves multiple domain events to outbox.
    """
    # Mock the SaveEventsToOutboxCommand class
    class MockSaveEventsToOutboxCommand:
        def __init__(self, events, correlation_id, db_session):
            self.events = events
            self.correlation_id = correlation_id
            self.db_session = db_session

    # Patch the import
    import sys
    from unittest.mock import MagicMock

    mock_outbox_module = MagicMock()
    mock_outbox_module.SaveEventsToOutboxCommand = MockSaveEventsToOutboxCommand
    sys.modules["libs.buildingblocks.messaging.outbox_cqrs"] = mock_outbox_module

    mock_mediator = AsyncMock()
    behavior = OutboxBehavior(mediator=mock_mediator)
    db_session = Mock()
    events = [
        {"type": "UserCreated", "user_id": "123"},
        {"type": "EmailSent", "email": "test@example.com"},
    ]
    command = CommandWithDomainEvents(
        events=events, db_session=db_session, correlation_id="test-456"
    )

    result = await behavior.handle(command, success_handler)

    assert result == "success"
    assert mock_mediator.send_command.called
    call_args = mock_mediator.send_command.call_args[0][0]
    assert hasattr(call_args, "events")
    assert call_args.events == events
    print("✅ OutboxBehavior saved multiple events")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_outbox_behavior_continues_on_save_failure(caplog):
    """
    Test that OutboxBehavior doesn't break business logic if outbox save fails.
    """
    import logging

    with caplog.at_level(logging.ERROR):
        mock_mediator = AsyncMock()
        mock_mediator.send_command.side_effect = Exception("Outbox save failed")
        behavior = OutboxBehavior(mediator=mock_mediator)
        db_session = Mock()
        command = CommandWithDomainEvents(
            events=["event1"], db_session=db_session, correlation_id="test-789"
        )

        # Should not raise, business logic succeeds even if outbox fails
        result = await behavior.handle(command, success_handler)

        assert result == "success"
        assert "Failed to save events to outbox" in caplog.text
    print("✅ OutboxBehavior continued on save failure")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_outbox_behavior_set_mediator():
    """
    Test that OutboxBehavior.set_mediator updates mediator reference.
    """
    behavior = OutboxBehavior(mediator=None)
    mock_mediator = AsyncMock()

    behavior.set_mediator(mock_mediator)

    assert behavior._mediator is mock_mediator
    print("✅ OutboxBehavior.set_mediator updated mediator")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_outbox_behavior_with_command_with_response(monkeypatch):
    """
    Test that OutboxBehavior processes ICommandWithResponse (not just ICommand).
    """
    # Mock the SaveEventToOutboxCommand class
    class MockSaveEventToOutboxCommand:
        def __init__(self, event, correlation_id, db_session):
            self.event = event
            self.correlation_id = correlation_id
            self.db_session = db_session

    # Patch the import
    import sys
    from unittest.mock import MagicMock

    mock_outbox_module = MagicMock()
    mock_outbox_module.SaveEventToOutboxCommand = MockSaveEventToOutboxCommand
    sys.modules["libs.buildingblocks.messaging.outbox_cqrs"] = mock_outbox_module

    mock_mediator = AsyncMock()
    behavior = OutboxBehavior(mediator=mock_mediator)
    db_session = Mock()

    class CommandWithResponse(ICommandWithResponse[str]):
        def __init__(self):
            self.domain_events = [{"type": "EventFromCommandWithResponse"}]
            self.db_session = db_session
            self.correlation_id = "test-999"

    command = CommandWithResponse()
    result = await behavior.handle(command, success_handler)

    assert result == "success"
    assert mock_mediator.send_command.called
    print("✅ OutboxBehavior processed ICommandWithResponse")
