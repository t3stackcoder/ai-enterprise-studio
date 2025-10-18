"""
Enterprise Mediator Pattern Implementation for CQRS
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from ..behaviors import IPipelineBehavior
from ..exceptions.pipeline_exceptions import HandlerNotFoundException, PipelineExecutionException
from .interfaces import (
    ICommand,
    ICommandHandler,
    ICommandHandlerWithResponse,
    ICommandWithResponse,
    IQuery,
    IQueryHandler,
)

TResponse = TypeVar("TResponse")


class IMediator(ABC):
    """
    Mediator interface for sending commands and queries
    """

    @abstractmethod
    async def send_command(self, command: ICommand) -> None:
        """Send a command with no return value"""
        pass

    @abstractmethod
    async def send_command_with_response(
        self, command: ICommandWithResponse[TResponse]
    ) -> TResponse:
        """Send a command that returns a response"""
        pass

    @abstractmethod
    async def send_query(self, query: IQuery[TResponse]) -> TResponse:
        """Send a query and get a response"""
        pass

    @abstractmethod
    def add_pipeline_behavior(self, behavior: IPipelineBehavior) -> None:
        """Add a pipeline behavior to the request processing pipeline"""
        pass


class EnterpriseMediator(IMediator):
    """
    Enterprise mediator with pipeline behaviors and dependency injection
    """

    def __init__(self):
        self._command_handlers: dict[type, Any] = {}
        self._command_with_response_handlers: dict[type, Any] = {}
        self._query_handlers: dict[type, Any] = {}
        self._pipeline_behaviors: list[IPipelineBehavior] = []

    def register_command_handler(
        self, command_type: type[ICommand], handler: ICommandHandler
    ) -> None:
        """Register a command handler"""
        self._command_handlers[command_type] = handler

    def register_command_with_response_handler(
        self, command_type: type[ICommandWithResponse], handler: ICommandHandlerWithResponse
    ) -> None:
        """Register a command handler that returns a response"""
        self._command_with_response_handlers[command_type] = handler

    def register_query_handler(self, query_type: type[IQuery], handler: IQueryHandler) -> None:
        """Register a query handler"""
        self._query_handlers[query_type] = handler

    def add_pipeline_behavior(self, behavior: IPipelineBehavior) -> None:
        """Add a pipeline behavior to the request processing pipeline"""
        self._pipeline_behaviors.append(behavior)

    async def _ensure_awaitable(self, result: Any) -> Any:
        """Ensure result is awaitable - if not, wrap it"""
        if asyncio.iscoroutine(result) or asyncio.isfuture(result):
            return await result
        return result

    async def send_command(self, command: ICommand) -> None:
        """Send a command with pipeline behaviors"""
        command_type = type(command)

        if command_type not in self._command_handlers:
            raise HandlerNotFoundException(command_type)

        handler = self._command_handlers[command_type]

        # Execute through pipeline behaviors
        try:
            await self._execute_pipeline(
                command, lambda: self._ensure_awaitable(handler.handle(command))
            )
        except Exception as e:
            if not isinstance(e, HandlerNotFoundException):
                raise PipelineExecutionException(
                    f"Command execution failed: {str(e)}",
                    command_type.__name__,
                    "CommandExecution",
                    e,
                ) from e
            raise

    async def send_command_with_response(
        self, command: ICommandWithResponse[TResponse]
    ) -> TResponse:
        """Send a command that returns a response with pipeline behaviors"""
        command_type = type(command)

        if command_type not in self._command_with_response_handlers:
            raise HandlerNotFoundException(command_type)

        handler = self._command_with_response_handlers[command_type]

        # Execute through pipeline behaviors
        try:
            return await self._execute_pipeline(
                command, lambda: self._ensure_awaitable(handler.handle(command))
            )
        except Exception as e:
            if not isinstance(e, HandlerNotFoundException):
                raise PipelineExecutionException(
                    f"Command with response execution failed: {str(e)}",
                    command_type.__name__,
                    "CommandWithResponseExecution",
                    e,
                ) from e
            raise

    async def send_query(self, query: IQuery[TResponse]) -> TResponse:
        """Send a query with pipeline behaviors"""
        query_type = type(query)

        if query_type not in self._query_handlers:
            raise HandlerNotFoundException(query_type)

        handler = self._query_handlers[query_type]

        # Execute through pipeline behaviors
        try:
            return await self._execute_pipeline(
                query, lambda: self._ensure_awaitable(handler.handle(query))
            )
        except Exception as e:
            if not isinstance(e, HandlerNotFoundException):
                raise PipelineExecutionException(
                    f"Query execution failed: {str(e)}", query_type.__name__, "QueryExecution", e
                ) from e
            raise

    async def _execute_pipeline(self, request: Any, final_handler) -> Any:
        """Execute request through pipeline behaviors"""
        if not self._pipeline_behaviors:
            return await final_handler()

        # Build the pipeline chain
        current_handler = final_handler

        # Wrap each behavior around the handler (reverse order)
        for behavior in reversed(self._pipeline_behaviors):
            # Capture the current handler in closure
            next_handler = current_handler

            async def create_handler(beh=behavior, nh=next_handler):
                return await beh.handle(request, nh)

            current_handler = create_handler

        # Execute the pipeline
        return await current_handler()


# Legacy Mediator for backward compatibility
class Mediator(EnterpriseMediator):
    """Legacy mediator - use EnterpriseMediator for new code"""

    def __init__(self):
        import warnings

        warnings.warn(
            "Mediator is deprecated, use EnterpriseMediator", DeprecationWarning, stacklevel=2
        )
        super().__init__()


# Enterprise dependency injection
_mediator_instance: IMediator = None


def get_mediator() -> IMediator:
    """
    FastAPI dependency for getting the mediator instance
    """
    global _mediator_instance
    if _mediator_instance is None:
        _mediator_instance = EnterpriseMediator()
    return _mediator_instance


def configure_mediator(
    mediator: IMediator | None = None,
    use_enterprise: bool = True,
    pipeline_behaviors: list[IPipelineBehavior] | None = None,
) -> IMediator:
    """Configure the global mediator instance with enterprise features"""
    global _mediator_instance

    if mediator:
        _mediator_instance = mediator
    elif use_enterprise:
        _mediator_instance = EnterpriseMediator()
    else:
        _mediator_instance = Mediator()

    # Add default pipeline behaviors
    if pipeline_behaviors and hasattr(_mediator_instance, "add_pipeline_behavior"):
        for behavior in pipeline_behaviors:
            _mediator_instance.add_pipeline_behavior(behavior)

    return _mediator_instance
