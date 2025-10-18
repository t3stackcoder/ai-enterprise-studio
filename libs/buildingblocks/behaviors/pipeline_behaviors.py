"""
Enterprise pipeline behaviors for CQRS commands and queries
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import BaseModel, ValidationError

TRequest = TypeVar("TRequest")
TResponse = TypeVar("TResponse")

logger = logging.getLogger(__name__)


class IPipelineBehavior(ABC):
    """Base interface for pipeline behaviors"""

    @abstractmethod
    async def handle(
        self, request: TRequest, next_handler: Callable[[], Awaitable[TResponse]]
    ) -> TResponse:
        """Handle the request and call the next behavior in the pipeline"""
        pass


class ValidationBehavior(IPipelineBehavior):
    """Enterprise validation behavior with detailed error reporting"""

    async def handle(
        self, request: TRequest, next_handler: Callable[[], Awaitable[TResponse]]
    ) -> TResponse:
        """Validate the request using Pydantic with enterprise error handling"""

        try:
            # Enhanced validation for Pydantic models
            if isinstance(request, BaseModel):
                # Re-validate to ensure all constraints are met
                request.model_validate(request.model_dump())
                logger.debug(f"Validated request: {type(request).__name__}")

            # Custom validation hook for non-Pydantic models (not BaseModel)
            elif hasattr(request, "validate") and callable(request.validate):
                validate_method = request.validate
                if asyncio.iscoroutinefunction(validate_method):
                    await validate_method()
                else:
                    validate_method()

        except ValidationError as e:
            logger.error(f"Validation failed for {type(request).__name__}: {e}")
            from ..exceptions.pipeline_exceptions import ValidationPipelineException

            error_messages = [str(error) for error in e.errors()]
            raise ValidationPipelineException(type(request).__name__, error_messages, e) from e
        except Exception as e:
            logger.error(f"Unexpected validation error for {type(request).__name__}: {e}")
            raise

        return await next_handler()


class LoggingBehavior(IPipelineBehavior):
    """Enterprise logging with performance monitoring and correlation IDs"""

    def __init__(self, slow_threshold: float = 3.0, enable_request_logging: bool = True):
        self.slow_threshold = slow_threshold
        self.enable_request_logging = enable_request_logging

    async def handle(
        self, request: TRequest, next_handler: Callable[[], Awaitable[TResponse]]
    ) -> TResponse:
        """Log request execution with enterprise monitoring"""

        request_name = type(request).__name__
        correlation_id = getattr(request, "correlation_id", None) or "unknown"

        # Log request details if enabled
        if self.enable_request_logging:
            logger.info(f"[START] [{correlation_id}] Handling {request_name}")

        start_time = time.time()

        try:
            response = await next_handler()
            execution_time = time.time() - start_time

            # Performance monitoring
            if execution_time > self.slow_threshold:
                logger.warning(
                    f"[PERFORMANCE] [{correlation_id}] {request_name} took {execution_time:.2f}s (threshold: {self.slow_threshold}s)"
                )

            logger.info(
                f"[SUCCESS] [{correlation_id}] {request_name} completed in {execution_time:.3f}s"
            )
            return response

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"[ERROR] [{correlation_id}] {request_name} failed after {execution_time:.3f}s: {str(e)}",
                exc_info=True,
            )
            raise


class AuthorizationBehavior(IPipelineBehavior):
    """Enterprise authorization behavior with role-based access control"""

    def __init__(self, require_authentication: bool = True):
        self.require_authentication = require_authentication

    async def handle(
        self, request: TRequest, next_handler: Callable[[], Awaitable[TResponse]]
    ) -> TResponse:
        """Enforce authorization rules"""

        # Check if user context is available
        user_context = getattr(request, "user_context", None)

        if self.require_authentication and not user_context:
            from ..exceptions.pipeline_exceptions import AuthorizationPipelineException

            raise AuthorizationPipelineException(type(request).__name__)

        # Custom authorization logic
        if hasattr(request, "authorize"):
            authorized = await request.authorize(user_context)
            if not authorized:
                from ..exceptions.pipeline_exceptions import AuthorizationPipelineException

                user_id = getattr(user_context, "user_id", None) if user_context else None
                raise AuthorizationPipelineException(
                    type(request).__name__, user_id, "custom_authorization"
                )

        return await next_handler()


class TransactionBehavior(IPipelineBehavior):
    """Enterprise transaction management with automatic rollback"""

    def __init__(self, auto_commit: bool = True):
        self.auto_commit = auto_commit

    async def handle(
        self, request: TRequest, next_handler: Callable[[], Awaitable[TResponse]]
    ) -> TResponse:
        """Manage database transactions"""

        # Check if request requires transaction
        if not hasattr(request, "requires_transaction") or not request.requires_transaction:
            return await next_handler()

        # Get database session from request context
        db_session = getattr(request, "db_session", None)
        if not db_session:
            logger.warning(
                f"Transaction requested but no db_session found for {type(request).__name__}"
            )
            return await next_handler()

        try:
            # Begin transaction if not already started
            if not db_session.in_transaction():
                db_session.begin()

            response = await next_handler()

            # Auto-commit if enabled
            if self.auto_commit:
                db_session.commit()
                logger.debug(f"Transaction committed for {type(request).__name__}")

            return response

        except Exception as e:
            # Rollback on any error
            db_session.rollback()
            logger.error(f"Transaction rolled back for {type(request).__name__}: {e}")
            from ..exceptions.pipeline_exceptions import TransactionPipelineException

            raise TransactionPipelineException(type(request).__name__, "rollback", e) from e


class CachingBehavior(IPipelineBehavior):
    """Enterprise caching behavior with TTL and cache invalidation"""

    def __init__(self, cache_ttl: int = 300, enable_caching: bool = True):
        self.cache_ttl = cache_ttl
        self.enable_caching = enable_caching
        self._cache: dict[str, tuple[float, any]] = {}

    async def handle(
        self, request: TRequest, next_handler: Callable[[], Awaitable[TResponse]]
    ) -> TResponse:
        """Cache query results"""

        # Only cache queries, not commands
        if not hasattr(request, "cache_key") or not self.enable_caching:
            return await next_handler()

        cache_key = request.cache_key
        current_time = time.time()

        # Check cache
        if cache_key in self._cache:
            cached_time, cached_result = self._cache[cache_key]
            if current_time - cached_time < self.cache_ttl:
                logger.debug(f"Cache hit for {type(request).__name__}: {cache_key}")
                return cached_result

        # Execute handler and cache result
        response = await next_handler()
        self._cache[cache_key] = (current_time, response)
        logger.debug(f"Cached result for {type(request).__name__}: {cache_key}")

        return response


class RateLimitingBehavior(IPipelineBehavior):
    """Enterprise rate limiting per user/workspace"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self._request_counts: dict[str, list[float]] = {}

    async def handle(
        self, request: TRequest, next_handler: Callable[[], Awaitable[TResponse]]
    ) -> TResponse:
        """Enforce rate limiting"""

        # Get rate limit key from request
        rate_limit_key = getattr(request, "rate_limit_key", None)
        if not rate_limit_key:
            return await next_handler()

        current_time = time.time()
        one_minute_ago = current_time - 60

        # Clean old requests
        if rate_limit_key in self._request_counts:
            self._request_counts[rate_limit_key] = [
                req_time
                for req_time in self._request_counts[rate_limit_key]
                if req_time > one_minute_ago
            ]
        else:
            self._request_counts[rate_limit_key] = []

        # Check rate limit
        if len(self._request_counts[rate_limit_key]) >= self.requests_per_minute:
            from ..exceptions.pipeline_exceptions import RateLimitExceededException

            raise RateLimitExceededException(rate_limit_key, self.requests_per_minute)

        # Record request
        self._request_counts[rate_limit_key].append(current_time)

        return await next_handler()


class CircuitBreakerBehavior(IPipelineBehavior):
    """Enterprise circuit breaker pattern for external service calls"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failure_counts: dict[str, int] = {}
        self._last_failure_times: dict[str, float] = {}

    async def handle(
        self, request: TRequest, next_handler: Callable[[], Awaitable[TResponse]]
    ) -> TResponse:
        """Implement circuit breaker pattern"""

        # Get circuit breaker key from request
        circuit_key = getattr(request, "circuit_breaker_key", None)
        if not circuit_key:
            return await next_handler()

        current_time = time.time()

        # Check if circuit is open
        if circuit_key in self._failure_counts:
            failure_count = self._failure_counts[circuit_key]
            last_failure_time = self._last_failure_times.get(circuit_key, 0)

            if (
                failure_count >= self.failure_threshold
                and current_time - last_failure_time < self.recovery_timeout
            ):
                from ..exceptions.pipeline_exceptions import CircuitBreakerOpenException

                raise CircuitBreakerOpenException(
                    circuit_key, failure_count, self.failure_threshold
                )

        try:
            response = await next_handler()
            # Reset failure count on success
            self._failure_counts[circuit_key] = 0
            return response

        except Exception:
            # Increment failure count
            self._failure_counts[circuit_key] = self._failure_counts.get(circuit_key, 0) + 1
            self._last_failure_times[circuit_key] = current_time
            logger.warning(
                f"Circuit breaker failure for {circuit_key}: {self._failure_counts[circuit_key]}/{self.failure_threshold}"
            )
            raise


class OutboxBehavior(IPipelineBehavior):
    """Enterprise transactional outbox behavior using pure CQRS"""

    def __init__(self, mediator=None):
        # Avoid circular import - mediator will be set when needed
        self._mediator = mediator

    def set_mediator(self, mediator):
        """Set mediator reference (avoid circular dependency)"""
        self._mediator = mediator

    async def handle(
        self, request: TRequest, next_handler: Callable[[], Awaitable[TResponse]]
    ) -> TResponse:
        """Automatically save domain events to outbox using CQRS"""

        # Execute the original command/query first
        response = await next_handler()

        # Only process domain events for commands (not queries)
        from ..cqrs.interfaces import ICommand, ICommandWithResponse

        if not isinstance(request, ICommand | ICommandWithResponse):
            return response

        # Check if request has domain events
        domain_events = getattr(request, "domain_events", None)
        if not domain_events:
            return response

        # Get database session and correlation ID from request
        db_session = getattr(request, "db_session", None)
        correlation_id = getattr(request, "correlation_id", None)

        if not db_session:
            logger.warning(
                f"OutboxBehavior: No db_session found for {type(request).__name__}, "
                "skipping event persistence"
            )
            return response

        if not self._mediator:
            logger.error("OutboxBehavior: No mediator configured, cannot save events to outbox")
            return response

        try:
            # Save all domain events to outbox using CQRS
            if len(domain_events) == 1:
                # Single event
                from ..messaging.outbox_cqrs import SaveEventToOutboxCommand

                save_command = SaveEventToOutboxCommand(
                    event=domain_events[0], correlation_id=correlation_id, db_session=db_session
                )
                await self._mediator.send_command(save_command)
            else:
                # Multiple events
                from ..messaging.outbox_cqrs import SaveEventsToOutboxCommand

                save_command = SaveEventsToOutboxCommand(
                    events=list(domain_events), correlation_id=correlation_id, db_session=db_session
                )
                await self._mediator.send_command(save_command)

            logger.debug(
                f"OutboxBehavior: Saved {len(domain_events)} events to outbox "
                f"for {type(request).__name__}"
            )

        except Exception as e:
            logger.error(
                f"OutboxBehavior: Failed to save events to outbox for "
                f"{type(request).__name__}: {e}"
            )
            # Don't re-raise - we don't want outbox failures to break business logic
            # Events will be lost, but the core operation succeeded

        return response
