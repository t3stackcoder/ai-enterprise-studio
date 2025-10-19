"""
Unit tests for CQRS Interfaces
"""

import pytest

from libs.buildingblocks.cqrs.interfaces import (
    ICommand,
    ICommandHandler,
    ICommandHandlerWithResponse,
    ICommandWithResponse,
    IQuery,
    IQueryHandler,
)


# Test implementations
class SampleCommand(ICommand):
    def __init__(self, value: str):
        self.value = value


class SampleCommandWithResponse(ICommandWithResponse[str]):
    def __init__(self, value: str):
        self.value = value


class SampleQuery(IQuery[int]):
    def __init__(self, count: int):
        self.count = count


class SampleCommandHandler(ICommandHandler[SampleCommand]):
    async def handle(self, command: SampleCommand) -> None:
        pass


class SampleCommandWithResponseHandler(
    ICommandHandlerWithResponse[SampleCommandWithResponse, str]
):
    async def handle(self, command: SampleCommandWithResponse) -> str:
        return f"Handled: {command.value}"


class SampleQueryHandler(IQueryHandler[SampleQuery, int]):
    async def handle(self, query: SampleQuery) -> int:
        return query.count * 2


@pytest.mark.unit
def test_command_interface_can_be_instantiated():
    """
    Test that ICommand marker interface can be inherited and instantiated.
    """
    command = SampleCommand(value="test")
    assert isinstance(command, ICommand)
    assert command.value == "test"
    print("✅ ICommand interface works")


@pytest.mark.unit
def test_command_with_response_interface():
    """
    Test that ICommandWithResponse can be inherited and instantiated.
    """
    command = SampleCommandWithResponse(value="test")
    assert isinstance(command, ICommandWithResponse)
    assert command.value == "test"
    print("✅ ICommandWithResponse interface works")


@pytest.mark.unit
def test_query_interface():
    """
    Test that IQuery interface can be inherited and instantiated.
    """
    query = SampleQuery(count=5)
    assert isinstance(query, IQuery)
    assert query.count == 5
    print("✅ IQuery interface works")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_command_handler_interface():
    """
    Test that ICommandHandler can be implemented and executed.
    """
    handler = SampleCommandHandler()
    command = SampleCommand(value="test")

    # Should not raise
    await handler.handle(command)
    print("✅ ICommandHandler interface works")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_command_with_response_handler_interface():
    """
    Test that ICommandHandlerWithResponse returns correct response.
    """
    handler = SampleCommandWithResponseHandler()
    command = SampleCommandWithResponse(value="test")

    result = await handler.handle(command)
    assert result == "Handled: test"
    print("✅ ICommandHandlerWithResponse interface works")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_query_handler_interface():
    """
    Test that IQueryHandler returns correct response.
    """
    handler = SampleQueryHandler()
    query = SampleQuery(count=5)

    result = await handler.handle(query)
    assert result == 10
    print("✅ IQueryHandler interface works")


@pytest.mark.unit
def test_command_handler_is_abstract():
    """
    Test that ICommandHandler cannot be instantiated without implementing handle.
    """

    class IncompleteHandler(ICommandHandler[SampleCommand]):
        pass  # Missing handle method

    with pytest.raises(TypeError):
        IncompleteHandler()

    print("✅ ICommandHandler enforces abstract method")


@pytest.mark.unit
def test_command_with_response_handler_is_abstract():
    """
    Test that ICommandHandlerWithResponse cannot be instantiated without handle.
    """

    class IncompleteHandler(ICommandHandlerWithResponse[SampleCommandWithResponse, str]):
        pass  # Missing handle method

    with pytest.raises(TypeError):
        IncompleteHandler()

    print("✅ ICommandHandlerWithResponse enforces abstract method")


@pytest.mark.unit
def test_query_handler_is_abstract():
    """
    Test that IQueryHandler cannot be instantiated without handle method.
    """

    class IncompleteHandler(IQueryHandler[SampleQuery, int]):
        pass  # Missing handle method

    with pytest.raises(TypeError):
        IncompleteHandler()

    print("✅ IQueryHandler enforces abstract method")
