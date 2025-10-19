"""
Unit tests for EnterpriseMediator - CQRS Core
"""

import asyncio
import warnings
from typing import Any

import pytest

from libs.buildingblocks.behaviors import IPipelineBehavior
from libs.buildingblocks.cqrs.interfaces import (
    ICommand,
    ICommandHandler,
    ICommandHandlerWithResponse,
    ICommandWithResponse,
    IQuery,
    IQueryHandler,
)
from libs.buildingblocks.cqrs.mediator import (
    EnterpriseMediator,
    IMediator,
    Mediator,
    configure_mediator,
    get_mediator,
)
from libs.buildingblocks.exceptions.pipeline_exceptions import (
    HandlerNotFoundException,
    PipelineExecutionException,
)


# Test Commands
class TestCommand(ICommand):
    def __init__(self, value: str):
        self.value = value
        self.executed = False


class TestCommandWithResponse(ICommandWithResponse[str]):
    def __init__(self, value: str):
        self.value = value


class TestQuery(IQuery[str]):
    def __init__(self, search: str):
        self.search = search


# Test Handlers
class TestCommandHandler(ICommandHandler[TestCommand]):
    def __init__(self):
        self.handled_commands = []

    async def handle(self, command: TestCommand) -> None:
        command.executed = True
        self.handled_commands.append(command)


class TestCommandWithResponseHandler(ICommandHandlerWithResponse[TestCommandWithResponse, str]):
    async def handle(self, command: TestCommandWithResponse) -> str:
        return f"Response: {command.value}"


class TestQueryHandler(IQueryHandler[TestQuery, str]):
    async def handle(self, query: TestQuery) -> str:
        return f"Found: {query.search}"


# Synchronous handlers (for testing _ensure_awaitable)
class SyncCommandHandler(ICommandHandler[TestCommand]):
    def handle(self, command: TestCommand) -> None:
        command.executed = True


class SyncCommandWithResponseHandler(ICommandHandlerWithResponse[TestCommandWithResponse, str]):
    def handle(self, command: TestCommandWithResponse) -> str:
        return f"Sync: {command.value}"


# Test Pipeline Behavior
class TestPipelineBehavior(IPipelineBehavior):
    def __init__(self):
        self.call_count = 0
        self.requests_seen = []

    async def handle(self, request: Any, next_handler) -> Any:
        self.call_count += 1
        self.requests_seen.append(request)
        result = await next_handler()
        return result


class OrderTrackingBehavior(IPipelineBehavior):
    def __init__(self, name: str, tracker: list):
        self.name = name
        self.tracker = tracker

    async def handle(self, request: Any, next_handler) -> Any:
        self.tracker.append(f"{self.name}_before")
        result = await next_handler()
        self.tracker.append(f"{self.name}_after")
        return result


# Tests
@pytest.mark.unit
@pytest.mark.asyncio
async def test_mediator_sends_command():
    """
    Test that mediator can send a basic command to registered handler.
    """
    mediator = EnterpriseMediator()
    handler = TestCommandHandler()
    mediator.register_command_handler(TestCommand, handler)

    command = TestCommand(value="test")
    await mediator.send_command(command)

    assert command.executed is True
    assert len(handler.handled_commands) == 1
    assert handler.handled_commands[0].value == "test"
    print("✅ Command dispatched and executed")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mediator_sends_command_with_response():
    """
    Test that mediator can send a command and receive response.
    """
    mediator = EnterpriseMediator()
    handler = TestCommandWithResponseHandler()
    mediator.register_command_with_response_handler(TestCommandWithResponse, handler)

    command = TestCommandWithResponse(value="hello")
    result = await mediator.send_command_with_response(command)

    assert result == "Response: hello"
    print("✅ Command with response executed successfully")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mediator_sends_query():
    """
    Test that mediator can send a query and receive result.
    """
    mediator = EnterpriseMediator()
    handler = TestQueryHandler()
    mediator.register_query_handler(TestQuery, handler)

    query = TestQuery(search="data")
    result = await mediator.send_query(query)

    assert result == "Found: data"
    print("✅ Query executed and returned result")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mediator_raises_handler_not_found():
    """
    Test that mediator raises HandlerNotFoundException for unregistered handlers.
    """
    mediator = EnterpriseMediator()

    # Command not registered
    command = TestCommand(value="test")
    with pytest.raises(HandlerNotFoundException):
        await mediator.send_command(command)

    # Command with response not registered
    command_with_response = TestCommandWithResponse(value="test")
    with pytest.raises(HandlerNotFoundException):
        await mediator.send_command_with_response(command_with_response)

    # Query not registered
    query = TestQuery(search="test")
    with pytest.raises(HandlerNotFoundException):
        await mediator.send_query(query)

    print("✅ HandlerNotFoundException raised for unregistered handlers")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mediator_pipeline_behaviors_execute():
    """
    Test that pipeline behaviors are executed during request processing.
    """
    mediator = EnterpriseMediator()
    behavior = TestPipelineBehavior()
    mediator.add_pipeline_behavior(behavior)

    handler = TestCommandHandler()
    mediator.register_command_handler(TestCommand, handler)

    command = TestCommand(value="test")
    await mediator.send_command(command)

    assert behavior.call_count == 1
    assert len(behavior.requests_seen) == 1
    assert behavior.requests_seen[0] == command
    print("✅ Pipeline behavior executed")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mediator_pipeline_behaviors_execute_in_order():
    """
    Test that multiple pipeline behaviors execute in correct order (FIFO wrapping).
    
    Behaviors are added: [A, B, C]
    Execution order should be: A_before → B_before → C_before → Handler → C_after → B_after → A_after
    """
    mediator = EnterpriseMediator()
    execution_order = []

    # Add behaviors in order
    behavior_a = OrderTrackingBehavior("A", execution_order)
    behavior_b = OrderTrackingBehavior("B", execution_order)
    behavior_c = OrderTrackingBehavior("C", execution_order)

    mediator.add_pipeline_behavior(behavior_a)
    mediator.add_pipeline_behavior(behavior_b)
    mediator.add_pipeline_behavior(behavior_c)

    handler = TestCommandHandler()
    mediator.register_command_handler(TestCommand, handler)

    command = TestCommand(value="test")
    await mediator.send_command(command)

    # Verify execution order
    expected_order = ["A_before", "B_before", "C_before", "C_after", "B_after", "A_after"]
    assert execution_order == expected_order
    print(f"✅ Pipeline behaviors executed in correct order: {execution_order}")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mediator_handles_sync_command_handler():
    """
    Test that mediator can handle synchronous command handlers via _ensure_awaitable.
    """
    mediator = EnterpriseMediator()
    handler = SyncCommandHandler()
    mediator.register_command_handler(TestCommand, handler)

    command = TestCommand(value="sync_test")
    await mediator.send_command(command)

    assert command.executed is True
    print("✅ Synchronous command handler executed successfully")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mediator_handles_sync_command_with_response_handler():
    """
    Test that mediator can handle synchronous command-with-response handlers.
    """
    mediator = EnterpriseMediator()
    handler = SyncCommandWithResponseHandler()
    mediator.register_command_with_response_handler(TestCommandWithResponse, handler)

    command = TestCommandWithResponse(value="sync_test")
    result = await mediator.send_command_with_response(command)

    assert result == "Sync: sync_test"
    print("✅ Synchronous command-with-response handler executed successfully")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mediator_wraps_handler_exceptions_in_pipeline_exception():
    """
    Test that exceptions from handlers are wrapped in PipelineExecutionException.
    """

    class FailingCommandHandler(ICommandHandler[TestCommand]):
        async def handle(self, command: TestCommand) -> None:
            raise ValueError("Handler failed!")

    mediator = EnterpriseMediator()
    handler = FailingCommandHandler()
    mediator.register_command_handler(TestCommand, handler)

    command = TestCommand(value="fail")

    with pytest.raises(PipelineExecutionException) as exc_info:
        await mediator.send_command(command)

    assert "Command execution failed" in str(exc_info.value)
    assert exc_info.value.behavior_type == "CommandExecution"
    assert exc_info.value.request_type == "TestCommand"
    print("✅ Handler exception wrapped in PipelineExecutionException")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mediator_pipeline_without_behaviors():
    """
    Test that mediator works correctly without any pipeline behaviors.
    """
    mediator = EnterpriseMediator()
    handler = TestCommandHandler()
    mediator.register_command_handler(TestCommand, handler)

    command = TestCommand(value="no_behaviors")
    await mediator.send_command(command)

    assert command.executed is True
    print("✅ Mediator works without pipeline behaviors")


@pytest.mark.unit
def test_legacy_mediator_shows_deprecation_warning():
    """
    Test that legacy Mediator class shows deprecation warning.
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        mediator = Mediator()

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "use EnterpriseMediator" in str(w[0].message)

    print("✅ Legacy Mediator shows deprecation warning")


@pytest.mark.unit
def test_get_mediator_returns_singleton():
    """
    Test that get_mediator returns the same instance (singleton pattern).
    """
    # Reset global instance
    import libs.buildingblocks.cqrs.mediator as mediator_module

    mediator_module._mediator_instance = None

    mediator1 = get_mediator()
    mediator2 = get_mediator()

    assert mediator1 is mediator2
    assert isinstance(mediator1, EnterpriseMediator)
    print("✅ get_mediator returns singleton instance")


@pytest.mark.unit
def test_configure_mediator_with_enterprise():
    """
    Test that configure_mediator creates EnterpriseMediator by default.
    """
    import libs.buildingblocks.cqrs.mediator as mediator_module

    mediator_module._mediator_instance = None

    mediator = configure_mediator(use_enterprise=True)

    assert isinstance(mediator, EnterpriseMediator)
    assert not isinstance(mediator, Mediator) or type(mediator).__name__ == "EnterpriseMediator"
    print("✅ configure_mediator creates EnterpriseMediator")


@pytest.mark.unit
def test_configure_mediator_with_custom_instance():
    """
    Test that configure_mediator accepts custom mediator instance.
    """
    import libs.buildingblocks.cqrs.mediator as mediator_module

    mediator_module._mediator_instance = None

    custom_mediator = EnterpriseMediator()
    result = configure_mediator(mediator=custom_mediator)

    assert result is custom_mediator
    print("✅ configure_mediator accepts custom instance")


@pytest.mark.unit
def test_configure_mediator_with_pipeline_behaviors():
    """
    Test that configure_mediator adds pipeline behaviors to mediator.
    """
    import libs.buildingblocks.cqrs.mediator as mediator_module

    mediator_module._mediator_instance = None

    behavior = TestPipelineBehavior()
    mediator = configure_mediator(use_enterprise=True, pipeline_behaviors=[behavior])

    assert len(mediator._pipeline_behaviors) == 1
    assert mediator._pipeline_behaviors[0] is behavior
    print("✅ configure_mediator adds pipeline behaviors")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mediator_multiple_commands_same_handler():
    """
    Test that mediator can handle multiple commands with same handler.
    """
    mediator = EnterpriseMediator()
    handler = TestCommandHandler()
    mediator.register_command_handler(TestCommand, handler)

    command1 = TestCommand(value="first")
    command2 = TestCommand(value="second")
    command3 = TestCommand(value="third")

    await mediator.send_command(command1)
    await mediator.send_command(command2)
    await mediator.send_command(command3)

    assert len(handler.handled_commands) == 3
    assert handler.handled_commands[0].value == "first"
    assert handler.handled_commands[1].value == "second"
    assert handler.handled_commands[2].value == "third"
    print("✅ Multiple commands handled by same handler")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mediator_concurrent_command_execution():
    """
    Test that mediator can handle concurrent command execution.
    """
    mediator = EnterpriseMediator()
    handler = TestCommandHandler()
    mediator.register_command_handler(TestCommand, handler)

    commands = [TestCommand(value=f"cmd_{i}") for i in range(10)]

    # Execute concurrently
    await asyncio.gather(*[mediator.send_command(cmd) for cmd in commands])

    assert len(handler.handled_commands) == 10
    assert all(cmd.executed for cmd in commands)
    print("✅ Concurrent command execution successful")
