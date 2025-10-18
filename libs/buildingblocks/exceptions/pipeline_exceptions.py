"""
Pipeline-specific exceptions for better error handling and testing
"""


class PipelineException(Exception):
    """Base exception for pipeline-related errors"""

    def __init__(
        self,
        message: str,
        request_type: str | None = None,
        inner_exception: Exception | None = None,
    ):
        self.message = message
        self.request_type = request_type
        self.inner_exception = inner_exception
        super().__init__(message)


class HandlerNotFoundException(PipelineException):
    """Raised when no handler is registered for a command or query type"""

    def __init__(self, request_type: type):
        message = f"No handler registered for request type: {request_type.__name__}"
        super().__init__(message, request_type.__name__)
        self.request_type_class = request_type


class PipelineExecutionException(PipelineException):
    """Wrapper for exceptions that occur during pipeline behavior execution"""

    def __init__(
        self, message: str, request_type: str, behavior_type: str, inner_exception: Exception
    ):
        full_message = f"Pipeline execution failed in {behavior_type} for {request_type}: {message}"
        super().__init__(full_message, request_type, inner_exception)
        self.behavior_type = behavior_type


class ValidationPipelineException(PipelineExecutionException):
    """Raised when validation fails in the pipeline"""

    def __init__(
        self, request_type: str, validation_errors: list[str], inner_exception: Exception = None
    ):
        message = f"Validation failed: {'; '.join(validation_errors)}"
        super().__init__(message, request_type, "ValidationBehavior", inner_exception)
        self.validation_errors = validation_errors


class AuthorizationPipelineException(PipelineExecutionException):
    """Raised when authorization fails in the pipeline"""

    def __init__(
        self,
        request_type: str,
        user_id: str | None = None,
        required_permission: str | None = None,
    ):
        if required_permission:
            message = (
                f"User {user_id or 'unknown'} lacks required permission: {required_permission}"
            )
        else:
            message = f"Authentication required for {request_type}"
        super().__init__(message, request_type, "AuthorizationBehavior", None)
        self.user_id = user_id
        self.required_permission = required_permission


class TransactionPipelineException(PipelineExecutionException):
    """Raised when transaction management fails in the pipeline"""

    def __init__(self, request_type: str, operation: str, inner_exception: Exception):
        message = f"Transaction {operation} failed"
        super().__init__(message, request_type, "TransactionBehavior", inner_exception)
        self.operation = operation


class RateLimitExceededException(PipelineExecutionException):
    """Raised when rate limiting threshold is exceeded"""

    def __init__(self, rate_limit_key: str, requests_per_minute: int):
        message = (
            f"Rate limit exceeded for '{rate_limit_key}': {requests_per_minute} requests/minute"
        )
        super().__init__(message, "RateLimiting", "RateLimitingBehavior", None)
        self.rate_limit_key = rate_limit_key
        self.requests_per_minute = requests_per_minute


class CircuitBreakerOpenException(PipelineExecutionException):
    """Raised when circuit breaker is in open state"""

    def __init__(self, circuit_key: str, failure_count: int, failure_threshold: int):
        message = f"Circuit breaker open for '{circuit_key}': {failure_count}/{failure_threshold} failures"
        super().__init__(message, "CircuitBreaker", "CircuitBreakerBehavior", None)
        self.circuit_key = circuit_key
        self.failure_count = failure_count
        self.failure_threshold = failure_threshold


class HandlerRegistrationException(PipelineException):
    """Raised when handler registration fails"""

    def __init__(self, handler_type: type, request_type: type, reason: str):
        message = (
            f"Failed to register {handler_type.__name__} for {request_type.__name__}: {reason}"
        )
        super().__init__(message, request_type.__name__)
        self.handler_type = handler_type
        self.request_type_class = request_type
        self.reason = reason
