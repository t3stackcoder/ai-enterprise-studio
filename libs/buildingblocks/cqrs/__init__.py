"""
Enterprise CQRS Building Blocks
"""

from .interfaces import (
    ICommand,
    ICommandHandler,
    ICommandHandlerWithResponse,
    ICommandWithResponse,
    IQuery,
    IQueryHandler,
)
from .mediator import EnterpriseMediator, IMediator, Mediator, configure_mediator, get_mediator
from .registration import HandlerDecorator, HandlerRegistry

__all__ = [
    # Interfaces
    "ICommand",
    "ICommandWithResponse",
    "IQuery",
    "ICommandHandler",
    "ICommandHandlerWithResponse",
    "IQueryHandler",
    # Mediator
    "IMediator",
    "EnterpriseMediator",
    "Mediator",  # Legacy
    "get_mediator",
    "configure_mediator",
    # Registration
    "HandlerRegistry",
    "HandlerDecorator",
]
