"""
CQRS Core Tests

Tests the fundamental CQRS building blocks: mediator routing, handler registration,
and command/query processing. These are practical tests that verify the mediator
actually routes requests to the correct handlers.
"""

import pytest
from building_blocks.cqrs.mediator import EnterpriseMediator
from building_blocks.cqrs.registration import HandlerRegistry
from building_blocks.exceptions.pipeline_exceptions import HandlerNotFoundException
from infrastructure_testing.mocks import MockHandler

from .builders import (
    BBCommandBuilder,
    BBMediatorBuilder,
    BBTestCreateUserCommand,
    BBTestGetUserQuery,
)


class TestMediatorRouting:
    """Test that mediator correctly routes commands and queries to handlers"""

    @pytest.mark.asyncio
    async def test_mediator_routes_command_to_registered_handler(self):
        """REAL TEST: Command reaches the correct handler"""
        # Given: Mediator with registered command handler
        mediator = EnterpriseMediator()
        mock_handler = MockHandler()
        mediator.register_command_handler(BBTestCreateUserCommand, mock_handler)

        # When: Send command
        command = BBTestCreateUserCommand(username="testuser", email="test@example.com")
        await mediator.send_command(command)

        # Then: Handler was called with the command
        mock_handler.assert_called_once_with("handle", command)

    @pytest.mark.asyncio
    async def test_mediator_routes_query_to_registered_handler(self):
        """REAL TEST: Query reaches the correct handler and returns response"""
        # Given: Mediator with registered query handler
        mediator = EnterpriseMediator()
        expected_response = {"user_id": "123", "username": "testuser"}
        mock_handler = MockHandler(response=expected_response)
        mediator.register_query_handler(BBTestGetUserQuery, mock_handler)

        # When: Send query
        query = BBTestGetUserQuery(user_id="123")
        result = await mediator.send_query(query)

        # Then: Handler was called and returned expected response
        mock_handler.assert_called_once_with("handle", query)
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_mediator_throws_exception_for_unregistered_handler(self):
        """REAL TEST: Mediator fails fast when no handler registered"""
        # Given: Mediator with no registered handlers
        mediator = EnterpriseMediator()

        # When: Send command with no registered handler
        command = BBTestCreateUserCommand(username="test", email="test@example.com")

        # Then: Should throw HandlerNotFoundException
        with pytest.raises(HandlerNotFoundException) as exc_info:
            await mediator.send_command(command)

        assert "BBTestCreateUserCommand" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mediator_with_multiple_handlers_routes_correctly(self):
        """REAL TEST: Multiple handlers are routed independently"""
        # Given: Mediator with multiple registered handlers
        mediator = EnterpriseMediator()
        user_handler = MockHandler()
        query_handler = MockHandler(response={"user_id": "123"})

        mediator.register_command_handler(BBTestCreateUserCommand, user_handler)
        mediator.register_query_handler(BBTestGetUserQuery, query_handler)

        # When: Send both command and query
        command = BBTestCreateUserCommand(username="user1", email="user1@example.com")
        query = BBTestGetUserQuery(user_id="123")

        await mediator.send_command(command)
        result = await mediator.send_query(query)

        # Then: Each handler was called with correct request
        user_handler.assert_called_once_with("handle", command)
        query_handler.assert_called_once_with("handle", query)
        assert result == {"user_id": "123"}


class TestHandlerRegistration:
    """Test automatic handler discovery and registration"""

    def test_handler_registry_extracts_request_type_from_generic_handler(self):
        """REAL TEST: Registry can determine what request type a handler handles"""

        from building_blocks.cqrs.interfaces import ICommandHandler

        # Given: A handler class with generic type annotation
        class TestUserHandler(ICommandHandler[BBTestCreateUserCommand]):
            async def handle(self, command: BBTestCreateUserCommand) -> None:
                pass

        # When: Extract request type
        request_type = HandlerRegistry.get_request_type_from_handler(TestUserHandler)

        # Then: Should correctly identify the command type
        assert request_type == BBTestCreateUserCommand

    def test_handler_registry_determines_handler_type(self):
        """REAL TEST: Registry can classify handler types"""
        from building_blocks.cqrs.interfaces import ICommandHandler, IQueryHandler

        # Given: Different handler types
        class CommandHandler(ICommandHandler[BBTestCreateUserCommand]):
            async def handle(self, command: BBTestCreateUserCommand) -> None:
                pass

        class QueryHandler(IQueryHandler[BBTestGetUserQuery, dict]):
            async def handle(self, query: BBTestGetUserQuery) -> dict:
                return {}

        # When: Determine handler types
        command_type = HandlerRegistry.get_handler_type(CommandHandler)
        query_type = HandlerRegistry.get_handler_type(QueryHandler)

        # Then: Should correctly classify each handler
        assert command_type == "command"
        assert query_type == "query"

    @pytest.mark.asyncio
    async def test_auto_registration_registers_handlers_correctly(self):
        """REAL TEST: Auto registration wires up handlers to mediator"""
        from building_blocks.cqrs.interfaces import ICommandHandler

        # Given: Handler class and mediator
        class AutoTestHandler(ICommandHandler[BBTestCreateUserCommand]):
            async def handle(self, command: BBTestCreateUserCommand) -> None:
                self.last_command = command

        mediator = EnterpriseMediator()
        handlers = [AutoTestHandler]

        # When: Auto-register handlers
        result = HandlerRegistry.auto_register_handlers(mediator, handlers)

        # Then: Handler should be registered successfully
        assert len(result["registered"]) == 1
        assert len(result["errors"]) == 0
        assert result["registered"][0]["handler_class"] == "AutoTestHandler"
        assert result["registered"][0]["request_type"] == "BBTestCreateUserCommand"

        # And: Mediator should route to the registered handler
        command = BBTestCreateUserCommand(username="auto", email="auto@example.com")
        await mediator.send_command(command)


class TestMediatorBuilder:
    """Test the BB mediator builder utility"""

    @pytest.mark.asyncio
    async def test_bb_mediator_builder_creates_configured_mediator(self):
        """REAL TEST: Builder creates working mediator with test handlers"""
        # Given: Builder with test handlers
        builder = BBMediatorBuilder()
        mediator = builder.with_test_handlers().build()

        # When: Send test command and query
        command = BBTestCreateUserCommand(username="buildertest", email="test@example.com")
        query = BBTestGetUserQuery(user_id="123")

        await mediator.send_command(command)
        result = await mediator.send_query(query)

        # Then: Should work without errors and return expected responses
        assert result == {"user_id": "123", "username": "test"}

    @pytest.mark.asyncio
    async def test_bb_command_builder_creates_commands_with_context(self):
        """REAL TEST: Command builder creates commands with proper context"""
        # Given: Command builder with context
        builder = BBCommandBuilder()

        # When: Build command with user context
        command = (
            builder.with_user_context("user123", roles=["admin"], permissions={"create_user"})
            .with_workspace("workspace456")
            .create_user_command(username="contexttest", email="context@example.com")
        )

        # Then: Command should have context attached
        assert command.user_id == "user123"
        assert command.user_roles == ["admin"]
        assert command.permissions == {"create_user"}
        assert command.workspace_id == "workspace456"
        assert command.username == "contexttest"
        assert command.email == "context@example.com"
