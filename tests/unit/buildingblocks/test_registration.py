"""
Unit tests for HandlerRegistry and HandlerDecorator
"""

import pytest
from typing import Any
from libs.buildingblocks.cqrs.registration import HandlerRegistry, HandlerDecorator
from libs.buildingblocks.cqrs.mediator import EnterpriseMediator
from libs.buildingblocks.cqrs.interfaces import (
    ICommand,
    ICommandHandler,
    ICommandWithResponse,
    ICommandHandlerWithResponse,
    IQuery,
    IQueryHandler,
)
from libs.buildingblocks.exceptions.pipeline_exceptions import HandlerRegistrationException


# Test Commands and Queries
class TestRegistrationCommand(ICommand):
    pass


class TestRegistrationCommandWithResponse(ICommandWithResponse[str]):
    pass


class TestRegistrationQuery(IQuery[int]):
    pass


# Test Handlers with proper generic types
class TestRegistrationCommandHandler(ICommandHandler[TestRegistrationCommand]):
    async def handle(self, command: TestRegistrationCommand) -> None:
        pass


class TestRegistrationCommandWithResponseHandler(
    ICommandHandlerWithResponse[TestRegistrationCommandWithResponse, str]
):
    async def handle(self, command: TestRegistrationCommandWithResponse) -> str:
        return "test_response"


class TestRegistrationQueryHandler(IQueryHandler[TestRegistrationQuery, int]):
    async def handle(self, query: TestRegistrationQuery) -> int:
        return 42


# Handler without generic type information (edge case)
class HandlerWithoutGenerics(ICommandHandler):
    def handle(self, command: TestRegistrationCommand) -> None:
        pass


# Invalid handler (doesn't implement handler interface)
class NotAHandler:
    def handle(self, something):
        pass


# ============================================================================
# HandlerRegistry.get_request_type_from_handler Tests
# ============================================================================


@pytest.mark.unit
def test_get_request_type_from_command_handler():
    """
    Test extracting request type from command handler.
    """
    request_type = HandlerRegistry.get_request_type_from_handler(TestRegistrationCommandHandler)

    assert request_type == TestRegistrationCommand
    print("✅ Extracted request type from command handler")


@pytest.mark.unit
def test_get_request_type_from_command_with_response_handler():
    """
    Test extracting request type from command with response handler.
    """
    request_type = HandlerRegistry.get_request_type_from_handler(
        TestRegistrationCommandWithResponseHandler
    )

    assert request_type == TestRegistrationCommandWithResponse
    print("✅ Extracted request type from command with response handler")


@pytest.mark.unit
def test_get_request_type_from_query_handler():
    """
    Test extracting request type from query handler.
    """
    request_type = HandlerRegistry.get_request_type_from_handler(TestRegistrationQueryHandler)

    assert request_type == TestRegistrationQuery
    print("✅ Extracted request type from query handler")


@pytest.mark.unit
def test_get_request_type_fallback_to_annotations():
    """
    Test fallback to __annotations__ when __orig_bases__ doesn't work.
    """
    # HandlerWithoutGenerics should fall back to checking handle method annotations
    request_type = HandlerRegistry.get_request_type_from_handler(HandlerWithoutGenerics)

    assert request_type == TestRegistrationCommand
    print("✅ Fallback to annotations worked")


@pytest.mark.unit
def test_get_request_type_raises_on_invalid_handler():
    """
    Test that HandlerRegistrationException is raised for invalid handlers.
    """
    with pytest.raises(HandlerRegistrationException) as exc_info:
        HandlerRegistry.get_request_type_from_handler(NotAHandler)

    assert "Could not determine request type" in str(exc_info.value)
    print("✅ Raised exception for invalid handler")


# ============================================================================
# HandlerRegistry.get_handler_type Tests
# ============================================================================


@pytest.mark.unit
def test_get_handler_type_for_command():
    """
    Test determining handler type for command handler.
    """
    handler_type = HandlerRegistry.get_handler_type(TestRegistrationCommandHandler)

    assert handler_type == "command"
    print("✅ Determined handler type as 'command'")


@pytest.mark.unit
def test_get_handler_type_for_command_with_response():
    """
    Test determining handler type for command with response handler.
    """
    handler_type = HandlerRegistry.get_handler_type(TestRegistrationCommandWithResponseHandler)

    assert handler_type == "command_with_response"
    print("✅ Determined handler type as 'command_with_response'")


@pytest.mark.unit
def test_get_handler_type_for_query():
    """
    Test determining handler type for query handler.
    """
    handler_type = HandlerRegistry.get_handler_type(TestRegistrationQueryHandler)

    assert handler_type == "query"
    print("✅ Determined handler type as 'query'")


@pytest.mark.unit
def test_get_handler_type_fallback_to_direct_inheritance():
    """
    Test fallback to direct inheritance check when __orig_bases__ is not available.
    """
    # HandlerWithoutGenerics should work via direct inheritance check
    handler_type = HandlerRegistry.get_handler_type(HandlerWithoutGenerics)

    assert handler_type == "command"
    print("✅ Fallback to direct inheritance worked")


@pytest.mark.unit
def test_get_handler_type_raises_on_invalid_handler():
    """
    Test that HandlerRegistrationException is raised for non-handler classes.
    """
    with pytest.raises(HandlerRegistrationException) as exc_info:
        HandlerRegistry.get_handler_type(NotAHandler)

    assert "does not implement a recognized handler interface" in str(exc_info.value)
    print("✅ Raised exception for invalid handler type")


# ============================================================================
# HandlerRegistry.auto_register_handlers Tests
# ============================================================================


@pytest.mark.unit
def test_auto_register_command_handler():
    """
    Test auto-registering a command handler.
    """
    mediator = EnterpriseMediator()
    handler_classes = [TestRegistrationCommandHandler]

    results = HandlerRegistry.auto_register_handlers(mediator, handler_classes)

    assert len(results["registered"]) == 1
    assert results["registered"][0]["handler_class"] == "TestRegistrationCommandHandler"
    assert results["registered"][0]["request_type"] == "TestRegistrationCommand"
    assert results["registered"][0]["handler_type"] == "command"
    assert len(results["errors"]) == 0
    print("✅ Auto-registered command handler")


@pytest.mark.unit
def test_auto_register_command_with_response_handler():
    """
    Test auto-registering a command with response handler.
    """
    mediator = EnterpriseMediator()
    handler_classes = [TestRegistrationCommandWithResponseHandler]

    results = HandlerRegistry.auto_register_handlers(mediator, handler_classes)

    assert len(results["registered"]) == 1
    assert results["registered"][0]["handler_type"] == "command_with_response"
    assert len(results["errors"]) == 0
    print("✅ Auto-registered command with response handler")


@pytest.mark.unit
def test_auto_register_query_handler():
    """
    Test auto-registering a query handler.
    """
    mediator = EnterpriseMediator()
    handler_classes = [TestRegistrationQueryHandler]

    results = HandlerRegistry.auto_register_handlers(mediator, handler_classes)

    assert len(results["registered"]) == 1
    assert results["registered"][0]["handler_type"] == "query"
    assert len(results["errors"]) == 0
    print("✅ Auto-registered query handler")


@pytest.mark.unit
def test_auto_register_multiple_handlers():
    """
    Test auto-registering multiple handlers at once.
    """
    mediator = EnterpriseMediator()
    handler_classes = [
        TestRegistrationCommandHandler,
        TestRegistrationCommandWithResponseHandler,
        TestRegistrationQueryHandler,
    ]

    results = HandlerRegistry.auto_register_handlers(mediator, handler_classes)

    assert len(results["registered"]) == 3
    assert len(results["errors"]) == 0
    print("✅ Auto-registered multiple handlers")


@pytest.mark.unit
def test_auto_register_handles_errors_gracefully():
    """
    Test that auto_register_handlers collects errors without crashing.
    """
    mediator = EnterpriseMediator()
    handler_classes = [
        TestRegistrationCommandHandler,  # Valid
        NotAHandler,  # Invalid - should error
        TestRegistrationQueryHandler,  # Valid
    ]

    results = HandlerRegistry.auto_register_handlers(mediator, handler_classes)

    assert len(results["registered"]) == 2  # Two valid handlers
    assert len(results["errors"]) == 1  # One error
    assert results["errors"][0]["handler_class"] == "NotAHandler"
    print("✅ Auto-register handled errors gracefully")


# ============================================================================
# HandlerRegistry.discover_handlers_in_module Tests
# ============================================================================


@pytest.mark.unit
def test_discover_handlers_in_module():
    """
    Test discovering handlers in the current test module.
    """
    import sys

    current_module = sys.modules[__name__]

    discovered = HandlerRegistry.discover_handlers_in_module(current_module)

    # Should find our test handlers
    handler_names = [h.__name__ for h in discovered]
    assert "TestRegistrationCommandHandler" in handler_names
    assert "TestRegistrationCommandWithResponseHandler" in handler_names
    assert "TestRegistrationQueryHandler" in handler_names
    assert "HandlerWithoutGenerics" in handler_names

    # Should NOT find the interface classes or non-handlers
    assert "ICommandHandler" not in handler_names
    assert "NotAHandler" not in handler_names
    print("✅ Discovered handlers in module")


@pytest.mark.unit
def test_discover_handlers_excludes_interface_classes():
    """
    Test that discover_handlers_in_module excludes the interface base classes.
    """
    import sys

    current_module = sys.modules[__name__]

    discovered = HandlerRegistry.discover_handlers_in_module(current_module)

    # Should not include the interface base classes themselves
    assert ICommandHandler not in discovered
    assert ICommandHandlerWithResponse not in discovered
    assert IQueryHandler not in discovered
    print("✅ Excluded interface base classes from discovery")


# ============================================================================
# HandlerDecorator Tests
# ============================================================================


@pytest.mark.unit
def test_command_handler_decorator():
    """
    Test @command_handler decorator adds metadata to handler class.
    """

    @HandlerDecorator.command_handler(TestRegistrationCommand)
    class DecoratedCommandHandler(ICommandHandler[TestRegistrationCommand]):
        async def handle(self, command: TestRegistrationCommand) -> None:
            pass

    assert hasattr(DecoratedCommandHandler, "_command_type")
    assert DecoratedCommandHandler._command_type == TestRegistrationCommand
    assert DecoratedCommandHandler._handler_type == "command"
    print("✅ @command_handler decorator applied metadata")


@pytest.mark.unit
def test_command_with_response_handler_decorator():
    """
    Test @command_with_response_handler decorator.
    """

    @HandlerDecorator.command_with_response_handler(TestRegistrationCommandWithResponse)
    class DecoratedCommandWithResponseHandler(
        ICommandHandlerWithResponse[TestRegistrationCommandWithResponse, str]
    ):
        async def handle(self, command: TestRegistrationCommandWithResponse) -> str:
            return "decorated"

    assert hasattr(DecoratedCommandWithResponseHandler, "_command_type")
    assert (
        DecoratedCommandWithResponseHandler._command_type == TestRegistrationCommandWithResponse
    )
    assert DecoratedCommandWithResponseHandler._handler_type == "command_with_response"
    print("✅ @command_with_response_handler decorator applied metadata")


@pytest.mark.unit
def test_query_handler_decorator():
    """
    Test @query_handler decorator.
    """

    @HandlerDecorator.query_handler(TestRegistrationQuery)
    class DecoratedQueryHandler(IQueryHandler[TestRegistrationQuery, int]):
        async def handle(self, query: TestRegistrationQuery) -> int:
            return 99

    assert hasattr(DecoratedQueryHandler, "_query_type")
    assert DecoratedQueryHandler._query_type == TestRegistrationQuery
    assert DecoratedQueryHandler._handler_type == "query"
    print("✅ @query_handler decorator applied metadata")


# ============================================================================
# Integration Test: Full Registration Flow
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_registration_and_execution_flow():
    """
    Integration test: Discover, register, and execute handlers.
    """
    import sys

    current_module = sys.modules[__name__]

    # Discover handlers
    discovered = HandlerRegistry.discover_handlers_in_module(current_module)
    assert len(discovered) > 0

    # Auto-register
    mediator = EnterpriseMediator()
    results = HandlerRegistry.auto_register_handlers(mediator, discovered)
    assert len(results["registered"]) > 0

    # Execute a command (verify registration worked)
    command = TestRegistrationCommand()
    await mediator.send_command(command)  # Should not raise

    # Execute a query
    query = TestRegistrationQuery()
    result = await mediator.send_query(query)
    assert result == 42

    print("✅ Full registration and execution flow succeeded")


# ============================================================================
# Edge Cases for Missing Coverage Lines
# ============================================================================


@pytest.mark.unit
def test_get_handler_type_direct_inheritance_command():
    """
    Test get_handler_type with direct ICommandHandler inheritance (no generics).
    This exercises the fallback path for line 100.
    Classes without generic parameters naturally don't have __orig_bases__,
    so the code falls back to issubclass checks.
    """

    # Create a handler class without __orig_bases__ by directly inheriting (no generics)
    class DirectCommandHandler(ICommandHandler):
        def handle(self, command):
            pass

    # This class won't have __orig_bases__ because it doesn't use generics
    handler_type = HandlerRegistry.get_handler_type(DirectCommandHandler)
    assert handler_type == "command"
    print("✅ Direct inheritance fallback for ICommandHandler (line 100)")


@pytest.mark.unit
def test_get_handler_type_direct_inheritance_query():
    """
    Test get_handler_type with direct IQueryHandler inheritance.
    This exercises the fallback path for line 104.
    """

    # Create a handler class without __orig_bases__ (no generics)
    class DirectQueryHandler(IQueryHandler):
        def handle(self, query):
            pass

    # This will use the fallback direct inheritance check
    handler_type = HandlerRegistry.get_handler_type(DirectQueryHandler)
    assert handler_type == "query"
    print("✅ Direct inheritance fallback for IQueryHandler (line 104)")
