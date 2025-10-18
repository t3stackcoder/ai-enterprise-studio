"""
Core domain exceptions for VisionScope
"""


class DomainException(Exception):
    """Base exception for all domain-specific errors"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundException(DomainException):
    """Raised when a requested entity is not found"""

    def __init__(self, entity_name: str, identifier: str | int):
        message = f"Entity '{entity_name}' with identifier '{identifier}' was not found"
        super().__init__(message)
        self.entity_name = entity_name
        self.identifier = identifier


class DuplicateEntityException(DomainException):
    """Raised when trying to create an entity that already exists"""

    def __init__(self, entity_name: str, identifier: str | int):
        message = f"Entity '{entity_name}' with identifier '{identifier}' already exists"
        super().__init__(message)
        self.entity_name = entity_name
        self.identifier = identifier


class ValidationException(DomainException):
    """Raised when validation fails"""

    def __init__(self, field: str, message: str):
        full_message = f"Validation failed for '{field}': {message}"
        super().__init__(full_message)
        self.field = field
        self.validation_message = message


class UnauthorizedException(DomainException):
    """Raised when user lacks permission for an operation"""

    def __init__(self, operation: str = "this operation"):
        message = f"Unauthorized access to {operation}"
        super().__init__(message)
        self.operation = operation
