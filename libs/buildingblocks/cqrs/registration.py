"""
Handler registration utilities for automatic discovery and registration
"""

import inspect
from typing import Any, get_args, get_origin

from ..exceptions.pipeline_exceptions import HandlerRegistrationException
from .interfaces import (
    ICommand,
    ICommandHandler,
    ICommandHandlerWithResponse,
    ICommandWithResponse,
    IQuery,
    IQueryHandler,
)
from .mediator import IMediator


class HandlerRegistry:
    """
    Utility class for automatic handler discovery and registration
    """

    @staticmethod
    def get_request_type_from_handler(handler_class: type) -> type:
        """
        Extract the request type (command/query) from a handler class using generic type inspection

        Args:
            handler_class: The handler class to inspect

        Returns:
            The request type that the handler handles

        Raises:
            HandlerRegistrationException: If the request type cannot be determined
        """
        try:
            # Get the original bases (generic base classes)
            orig_bases = getattr(handler_class, "__orig_bases__", ())

            for base in orig_bases:
                origin = get_origin(base)
                args = get_args(base)

                # Check if this is a handler interface with type arguments
                if (
                    origin
                    and args
                    and issubclass(
                        origin, ICommandHandler | ICommandHandlerWithResponse | IQueryHandler
                    )
                ):
                    return args[0]  # First type argument is the request type

            # Fallback: check __annotations__ for handle method
            handle_method = getattr(handler_class, "handle", None)
            if handle_method:
                annotations = getattr(handle_method, "__annotations__", {})
                for param_name, param_type in annotations.items():
                    if param_name != "return" and param_type is not type(None):
                        return param_type

            raise HandlerRegistrationException(
                handler_class, object, "Could not determine request type from handler class"
            )

        except Exception as e:
            raise HandlerRegistrationException(
                handler_class, object, f"Failed to extract request type: {str(e)}"
            ) from e

    @staticmethod
    def get_handler_type(handler_class: type) -> str:
        """
        Determine the type of handler (command, command_with_response, or query)

        Args:
            handler_class: The handler class to inspect

        Returns:
            Handler type as string: 'command', 'command_with_response', or 'query'
        """
        # Check original bases for handler interfaces
        orig_bases = getattr(handler_class, "__orig_bases__", ())

        for base in orig_bases:
            origin = get_origin(base)
            if origin:
                if issubclass(origin, ICommandHandlerWithResponse):
                    return "command_with_response"
                elif issubclass(origin, ICommandHandler):
                    return "command"
                elif issubclass(origin, IQueryHandler):
                    return "query"

        # Fallback: check direct inheritance
        if issubclass(handler_class, ICommandHandlerWithResponse):
            return "command_with_response"
        elif issubclass(handler_class, ICommandHandler):
            return "command"
        elif issubclass(handler_class, IQueryHandler):
            return "query"

        raise HandlerRegistrationException(
            handler_class, object, "Handler class does not implement a recognized handler interface"
        )

    @staticmethod
    def auto_register_handlers(mediator: IMediator, handler_classes: list[type]) -> dict[str, Any]:
        """
        Auto-register a list of handler classes with the mediator

        Args:
            mediator: The mediator to register handlers with
            handler_classes: List of handler classes to register

        Returns:
            Dictionary containing registration results and any errors
        """
        results = {"registered": [], "errors": []}

        for handler_class in handler_classes:
            try:
                request_type = HandlerRegistry.get_request_type_from_handler(handler_class)
                handler_type = HandlerRegistry.get_handler_type(handler_class)

                # Create handler instance
                handler_instance = handler_class()

                # Register based on handler type
                if handler_type == "command":
                    mediator.register_command_handler(request_type, handler_instance)
                elif handler_type == "command_with_response":
                    mediator.register_command_with_response_handler(request_type, handler_instance)
                elif handler_type == "query":
                    mediator.register_query_handler(request_type, handler_instance)

                results["registered"].append(
                    {
                        "handler_class": handler_class.__name__,
                        "request_type": request_type.__name__,
                        "handler_type": handler_type,
                    }
                )

            except Exception as e:
                results["errors"].append({"handler_class": handler_class.__name__, "error": str(e)})

        return results

    @staticmethod
    def discover_handlers_in_module(module: Any) -> list[type]:
        """
        Discover all handler classes in a module

        Args:
            module: The module to search for handler classes

        Returns:
            List of handler classes found in the module
        """
        handler_classes = []

        for name in dir(module):
            obj = getattr(module, name)

            # Check if it's a class and a handler
            if (
                inspect.isclass(obj)
                and (issubclass(obj, ICommandHandler | ICommandHandlerWithResponse | IQueryHandler))
                and obj not in (ICommandHandler, ICommandHandlerWithResponse, IQueryHandler)
            ):
                handler_classes.append(obj)

        return handler_classes


class HandlerDecorator:
    """
    Decorator utilities for marking and registering handlers
    """

    @staticmethod
    def command_handler(command_type: type[ICommand]):
        """
        Decorator to mark a class as a command handler for a specific command type

        Usage:
            @command_handler(CreateUserCommand)
            class CreateUserHandler(ICommandHandler[CreateUserCommand]):
                async def handle(self, command: CreateUserCommand) -> None:
                    pass
        """

        def decorator(handler_class):
            handler_class._command_type = command_type
            handler_class._handler_type = "command"
            return handler_class

        return decorator

    @staticmethod
    def command_with_response_handler(command_type: type[ICommandWithResponse]):
        """
        Decorator to mark a class as a command handler that returns a response
        """

        def decorator(handler_class):
            handler_class._command_type = command_type
            handler_class._handler_type = "command_with_response"
            return handler_class

        return decorator

    @staticmethod
    def query_handler(query_type: type[IQuery]):
        """
        Decorator to mark a class as a query handler for a specific query type
        """

        def decorator(handler_class):
            handler_class._query_type = query_type
            handler_class._handler_type = "query"
            return handler_class

        return decorator
