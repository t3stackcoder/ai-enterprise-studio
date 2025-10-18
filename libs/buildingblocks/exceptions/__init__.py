"""
Domain exceptions for VisionScope
"""

from .domain_exceptions import (
    DomainException,
    DuplicateEntityException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from .pipeline_exceptions import (
    AuthorizationPipelineException,
    CircuitBreakerOpenException,
    HandlerNotFoundException,
    HandlerRegistrationException,
    PipelineException,
    PipelineExecutionException,
    RateLimitExceededException,
    TransactionPipelineException,
    ValidationPipelineException,
)

__all__ = [
    # Domain exceptions
    "DomainException",
    "NotFoundException",
    "DuplicateEntityException",
    "ValidationException",
    "UnauthorizedException",
    # Pipeline exceptions
    "PipelineException",
    "HandlerNotFoundException",
    "PipelineExecutionException",
    "ValidationPipelineException",
    "AuthorizationPipelineException",
    "TransactionPipelineException",
    "RateLimitExceededException",
    "CircuitBreakerOpenException",
    "HandlerRegistrationException",
]
