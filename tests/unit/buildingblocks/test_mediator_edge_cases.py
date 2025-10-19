"""
Unit tests for EnterpriseMediator edge cases and missing coverage
"""

import pytest
import warnings
from libs.buildingblocks.cqrs.mediator import (
    EnterpriseMediator,
    Mediator,
    get_mediator,
    configure_mediator,
)
from libs.buildingblocks.cqrs.interfaces import (
    ICommand,
    ICommandHandler,
    ICommandWithResponse,
    ICommandHandlerWithResponse,
    IQuery,
    IQueryHandler,
)
from libs.buildingblocks.behaviors.pipeline_behaviors import IPipelineBehavior
from libs.buildingblocks.exceptions.pipeline_exceptions import (
    HandlerNotFoundException,
    PipelineExecutionException,
)


# Test commands and handlers
class EdgeCaseCommand(ICommand):
    pass


class EdgeCaseCommandHandler(ICommandHandler[EdgeCaseCommand]):
    def __init__(self):
        self.executed = False

    def handle(self, command: EdgeCaseCommand):
        """Sync handler (not async) - tests _ensure_awaitable"""
        self.executed = True
        return None  # Sync return


class EdgeCaseCommandWithResponse(ICommandWithResponse[str]):
    pass


class EdgeCaseCommandWithResponseHandler(ICommandHandlerWithResponse[EdgeCaseCommandWithResponse, str]):
    def handle(self, command: EdgeCaseCommandWithResponse):
        """Sync handler returning value"""
        return "sync_response"


class EdgeCaseQuery(IQuery[str]):
    pass


class EdgeCaseQueryHandler(IQueryHandler[EdgeCaseQuery, str]):
    def handle(self, query: EdgeCaseQuery):
        """Sync handler returning value"""
        return "sync_query_result"


class FailingCommandHandler(ICommandHandler[EdgeCaseCommand]):
    def handle(self, command: EdgeCaseCommand):
        raise ValueError("Handler intentionally failed")


class FailingCommandWithResponseHandler(ICommandHandlerWithResponse[EdgeCaseCommandWithResponse, str]):
    def handle(self, command: EdgeCaseCommandWithResponse):
        raise RuntimeError("CommandWithResponse handler failed")


class FailingQueryHandler(IQueryHandler[EdgeCaseQuery, str]):
    def handle(self, query: EdgeCaseQuery):
        raise IOError("Query handler failed")


# ============================================================================
# Sync Handler Tests (_ensure_awaitable coverage)
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_command_with_sync_handler():
    """
    Test send_command with synchronous handler (covers _ensure_awaitable for non-coroutines).
    Missing line 110: return result (non-async path)
    """
    mediator = EnterpriseMediator()
    handler = EdgeCaseCommandHandler()
    mediator.register_command_handler(EdgeCaseCommand, handler)

    command = EdgeCaseCommand()
    await mediator.send_command(command)

    assert handler.executed is True
    print("✅ send_command handled sync handler")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_command_with_response_sync_handler():
    """
    Test send_command_with_response with synchronous handler.
    Missing line 110: return result (non-async path)
    """
    mediator = EnterpriseMediator()
    handler = EdgeCaseCommandWithResponseHandler()
    mediator.register_command_with_response_handler(EdgeCaseCommandWithResponse, handler)

    command = EdgeCaseCommandWithResponse()
    result = await mediator.send_command_with_response(command)

    assert result == "sync_response"
    print("✅ send_command_with_response handled sync handler")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_query_with_sync_handler():
    """
    Test send_query with synchronous handler.
    Missing line 110: return result (non-async path)
    """
    mediator = EnterpriseMediator()
    handler = EdgeCaseQueryHandler()
    mediator.register_query_handler(EdgeCaseQuery, handler)

    query = EdgeCaseQuery()
    result = await mediator.send_query(query)

    assert result == "sync_query_result"
    print("✅ send_query handled sync handler")


# ============================================================================
# Pipeline Exception Wrapping Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_command_wraps_handler_exception_in_pipeline_exception():
    """
    Test that send_command wraps handler exceptions in PipelineExecutionException.
    Missing lines 128-136: Exception wrapping logic
    """
    mediator = EnterpriseMediator()
    handler = FailingCommandHandler()
    mediator.register_command_handler(EdgeCaseCommand, handler)

    with pytest.raises(PipelineExecutionException) as exc_info:
        await mediator.send_command(EdgeCaseCommand())

    assert "Command execution failed" in str(exc_info.value)
    assert exc_info.value.request_type == "EdgeCaseCommand"
    assert exc_info.value.behavior_type == "CommandExecution"
    assert isinstance(exc_info.value.__cause__, ValueError)
    print("✅ send_command wrapped exception in PipelineExecutionException")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_command_with_response_wraps_handler_exception():
    """
    Test that send_command_with_response wraps handler exceptions.
    Missing lines 152-157: Exception wrapping logic for CommandWithResponse
    """
    mediator = EnterpriseMediator()
    handler = FailingCommandWithResponseHandler()
    mediator.register_command_with_response_handler(EdgeCaseCommandWithResponse, handler)

    with pytest.raises(PipelineExecutionException) as exc_info:
        await mediator.send_command_with_response(EdgeCaseCommandWithResponse())

    assert "Command with response execution failed" in str(exc_info.value)
    assert exc_info.value.request_type == "EdgeCaseCommandWithResponse"
    assert exc_info.value.behavior_type == "CommandWithResponseExecution"
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    print("✅ send_command_with_response wrapped exception")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_query_wraps_handler_exception():
    """
    Test that send_query wraps handler exceptions.
    Missing line 221: Exception wrapping for queries (though coverage shows this might be working)
    """
    mediator = EnterpriseMediator()
    handler = FailingQueryHandler()
    mediator.register_query_handler(EdgeCaseQuery, handler)

    with pytest.raises(PipelineExecutionException) as exc_info:
        await mediator.send_query(EdgeCaseQuery())

    assert "Query execution failed" in str(exc_info.value)
    assert exc_info.value.request_type == "EdgeCaseQuery"
    assert exc_info.value.behavior_type == "QueryExecution"
    assert isinstance(exc_info.value.__cause__, IOError)
    print("✅ send_query wrapped exception")


# ============================================================================
# Handler Registration Edge Cases
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_command_with_response_handler():
    """
    Test register_command_with_response_handler method.
    Missing lines 31, 38, 43, 48: Registration methods
    """
    mediator = EnterpriseMediator()
    handler = EdgeCaseCommandWithResponseHandler()

    # This exercises the registration method
    mediator.register_command_with_response_handler(EdgeCaseCommandWithResponse, handler)

    # Verify registration worked
    command = EdgeCaseCommandWithResponse()
    result = await mediator.send_command_with_response(command)
    assert result == "sync_response"
    print("✅ register_command_with_response_handler worked")


# ============================================================================
# Legacy Mediator Tests
# ============================================================================


@pytest.mark.unit
def test_legacy_mediator_shows_deprecation_warning():
    """
    Test that legacy Mediator class shows deprecation warning.
    This covers the Mediator class __init__ which wraps warnings.warn
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        mediator = Mediator()

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "use EnterpriseMediator" in str(w[0].message)
        assert isinstance(mediator, EnterpriseMediator)
    print("✅ Legacy Mediator shows deprecation warning")


# ============================================================================
# Global Mediator Instance Tests
# ============================================================================


@pytest.mark.unit
def test_get_mediator_creates_instance_on_first_call():
    """
    Test get_mediator() creates singleton instance.
    """
    # Reset global state
    import libs.buildingblocks.cqrs.mediator as mediator_module

    mediator_module._mediator_instance = None

    mediator1 = get_mediator()
    mediator2 = get_mediator()

    assert mediator1 is not None
    assert mediator1 is mediator2  # Singleton
    assert isinstance(mediator1, EnterpriseMediator)
    print("✅ get_mediator creates singleton instance")


@pytest.mark.unit
def test_configure_mediator_with_custom_mediator():
    """
    Test configure_mediator with custom mediator instance.
    """
    custom_mediator = EnterpriseMediator()
    result = configure_mediator(mediator=custom_mediator)

    assert result is custom_mediator
    assert get_mediator() is custom_mediator
    print("✅ configure_mediator accepts custom mediator")


@pytest.mark.unit
def test_configure_mediator_with_legacy_flag():
    """
    Test configure_mediator with use_enterprise=False (creates legacy Mediator).
    """
    import libs.buildingblocks.cqrs.mediator as mediator_module

    mediator_module._mediator_instance = None

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = configure_mediator(use_enterprise=False)

        assert isinstance(result, Mediator)
    print("✅ configure_mediator created legacy Mediator")


@pytest.mark.unit
def test_configure_mediator_with_pipeline_behaviors():
    """
    Test configure_mediator adds pipeline behaviors.
    """
    import libs.buildingblocks.cqrs.mediator as mediator_module

    mediator_module._mediator_instance = None

    class MockBehavior(IPipelineBehavior):
        async def handle(self, request, next_handler):
            return await next_handler()

    behavior1 = MockBehavior()
    behavior2 = MockBehavior()

    result = configure_mediator(pipeline_behaviors=[behavior1, behavior2])

    assert len(result._pipeline_behaviors) == 2
    assert result._pipeline_behaviors[0] is behavior1
    assert result._pipeline_behaviors[1] is behavior2
    print("✅ configure_mediator added pipeline behaviors")


# ============================================================================
# HandlerNotFoundException Re-raising Tests (Lines 110, 136, 157)
# ============================================================================


class ThrowingBehavior(IPipelineBehavior):
    """Behavior that throws HandlerNotFoundException"""

    async def handle(self, request, next_handler):
        # Don't call next_handler, throw HandlerNotFoundException instead
        raise HandlerNotFoundException(type(request))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_command_reraises_handler_not_found_exception():
    """
    Test that send_command re-raises HandlerNotFoundException without wrapping.
    Missing line 110: raise (after catching HandlerNotFoundException)
    """
    mediator = EnterpriseMediator()
    handler = EdgeCaseCommandHandler()
    mediator.register_command_handler(EdgeCaseCommand, handler)
    mediator.add_pipeline_behavior(ThrowingBehavior())

    # Should re-raise HandlerNotFoundException, not wrap it
    with pytest.raises(HandlerNotFoundException) as exc_info:
        await mediator.send_command(EdgeCaseCommand())

    # Verify it's the original exception, not wrapped in PipelineExecutionException
    assert type(exc_info.value) == HandlerNotFoundException
    assert not isinstance(exc_info.value, PipelineExecutionException)
    print("✅ send_command re-raised HandlerNotFoundException")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_command_with_response_reraises_handler_not_found_exception():
    """
    Test that send_command_with_response re-raises HandlerNotFoundException.
    Missing line 136: raise (after catching HandlerNotFoundException)
    """
    mediator = EnterpriseMediator()
    handler = EdgeCaseCommandWithResponseHandler()
    mediator.register_command_with_response_handler(EdgeCaseCommandWithResponse, handler)
    mediator.add_pipeline_behavior(ThrowingBehavior())

    with pytest.raises(HandlerNotFoundException) as exc_info:
        await mediator.send_command_with_response(EdgeCaseCommandWithResponse())

    assert type(exc_info.value) == HandlerNotFoundException
    assert not isinstance(exc_info.value, PipelineExecutionException)
    print("✅ send_command_with_response re-raised HandlerNotFoundException")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_query_reraises_handler_not_found_exception():
    """
    Test that send_query re-raises HandlerNotFoundException.
    Missing line 157: raise (after catching HandlerNotFoundException)
    """
    mediator = EnterpriseMediator()
    handler = EdgeCaseQueryHandler()
    mediator.register_query_handler(EdgeCaseQuery, handler)
    mediator.add_pipeline_behavior(ThrowingBehavior())

    with pytest.raises(HandlerNotFoundException) as exc_info:
        await mediator.send_query(EdgeCaseQuery())

    assert type(exc_info.value) == HandlerNotFoundException
    assert not isinstance(exc_info.value, PipelineExecutionException)
    print("✅ send_query re-raised HandlerNotFoundException")
