"""
Building Blocks Testing Module

Tests for enterprise CQRS building blocks including mediator, pipeline behaviors,
outbox pattern, and context handling. Follows the infrastructure → domain pattern
established by the auth module.
"""

# Export test utilities and builders for use by other modules
from .builders import (
    BBCommandBuilder,
    BBMediatorBuilder,
    BBOutboxBuilder,
    BBPipelineBuilder,
    BBTestCreateUserCommand,
    BBTestGetUserQuery,
    BBTestProcessPaymentCommand,
)

__all__ = [
    "BBCommandBuilder",
    "BBMediatorBuilder",
    "BBPipelineBuilder",
    "BBOutboxBuilder",
    "BBTestCreateUserCommand",
    "BBTestGetUserQuery",
    "BBTestProcessPaymentCommand",
]
