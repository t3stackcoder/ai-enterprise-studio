"""
CQRS Interfaces for command and query separation
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

# Type variables for generic interfaces
TCommand = TypeVar("TCommand", bound="ICommand")
TQuery = TypeVar("TQuery", bound="IQuery")
TResponse = TypeVar("TResponse")


class ICommand:
    """
    Marker interface for commands (write operations)
    Commands using dataclasses can override __post_init__ for validation
    """

    pass


class ICommandWithResponse(Generic[TResponse]):
    """
    Command interface that returns a response
    """

    pass


class IQuery(Generic[TResponse]):
    """
    Base interface for queries (read operations)
    """

    pass


class ICommandHandler(ABC, Generic[TCommand]):
    """
    Handler for commands with no return value
    """

    @abstractmethod
    async def handle(self, command: TCommand) -> None:
        """Handle a command with no return value"""
        pass


class ICommandHandlerWithResponse(ABC, Generic[TCommand, TResponse]):
    """
    Handler for commands that return a response
    """

    @abstractmethod
    async def handle(self, command: TCommand) -> TResponse:
        """Handle a command and return a response"""
        pass


class IQueryHandler(ABC, Generic[TQuery, TResponse]):
    """
    Handler for queries (read operations)
    """

    @abstractmethod
    async def handle(self, query: TQuery) -> TResponse:
        """Handle a query and return a response"""
        pass
