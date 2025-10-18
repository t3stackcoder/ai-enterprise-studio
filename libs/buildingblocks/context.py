"""
Request context infrastructure for pipeline behaviors and cross-cutting concerns
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4


@dataclass
class RequestContext:
    """
    Container for cross-cutting request data used by pipeline behaviors
    """

    correlation_id: UUID = field(default_factory=uuid4)
    user_context: Any | None = None
    db_session: Any | None = None
    workspace_id: str | None = None
    request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Authorization context
    user_id: str | None = None
    user_roles: list[str] = field(default_factory=list)
    permissions: set[str] = field(default_factory=set)

    # Performance context
    rate_limit_key: str | None = None
    circuit_breaker_key: str | None = None
    cache_key: str | None = None

    # Transaction context
    requires_transaction: bool = False
    auto_commit: bool = True


def with_context(request: Any, context: RequestContext) -> Any:
    """
    Attach RequestContext to a request object for pipeline behaviors to use

    Args:
        request: The command or query object
        context: The RequestContext to attach

    Returns:
        The request object with context attached
    """
    # Attach all context attributes to the request
    for attr_name, attr_value in context.__dict__.items():
        setattr(request, attr_name, attr_value)

    return request


def get_context_from_request(request: Any) -> RequestContext:
    """
    Extract RequestContext from a request object

    Args:
        request: The command or query object with attached context

    Returns:
        RequestContext extracted from the request
    """
    context = RequestContext()

    # Extract context attributes from request if they exist
    for attr_name in context.__dict__.keys():
        if hasattr(request, attr_name):
            setattr(context, attr_name, getattr(request, attr_name))

    return context


class ContextBuilder:
    """
    Builder pattern for creating RequestContext objects in tests
    """

    def __init__(self):
        self._context = RequestContext()

    def with_user(
        self, user_id: str, roles: list[str] = None, permissions: set[str] = None
    ) -> "ContextBuilder":
        """Add user information to context"""
        self._context.user_id = user_id
        self._context.user_roles = roles or []
        self._context.permissions = permissions or set()
        return self

    def with_workspace(self, workspace_id: str) -> "ContextBuilder":
        """Add workspace information to context"""
        self._context.workspace_id = workspace_id
        return self

    def with_transaction(
        self, requires_transaction: bool = True, auto_commit: bool = True
    ) -> "ContextBuilder":
        """Add transaction information to context"""
        self._context.requires_transaction = requires_transaction
        self._context.auto_commit = auto_commit
        return self

    def with_rate_limiting(self, rate_limit_key: str) -> "ContextBuilder":
        """Add rate limiting information to context"""
        self._context.rate_limit_key = rate_limit_key
        return self

    def with_circuit_breaker(self, circuit_breaker_key: str) -> "ContextBuilder":
        """Add circuit breaker information to context"""
        self._context.circuit_breaker_key = circuit_breaker_key
        return self

    def with_caching(self, cache_key: str) -> "ContextBuilder":
        """Add caching information to context"""
        self._context.cache_key = cache_key
        return self

    def with_correlation_id(self, correlation_id: UUID) -> "ContextBuilder":
        """Add correlation ID to context"""
        self._context.correlation_id = correlation_id
        return self

    def build(self) -> RequestContext:
        """Build the RequestContext"""
        return self._context
