"""Custom exceptions for document service operations."""


class DocumentServiceError(Exception):
    """Base exception for document service errors."""

    pass


class ValidationError(DocumentServiceError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


class NotFoundError(DocumentServiceError):
    """Raised when a document is not found."""

    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(message)
        self.resource_type = resource_type
        self.resource_id = resource_id


class DuplicateError(DocumentServiceError):
    """Raised when attempting to create a duplicate resource."""

    def __init__(self, resource_type: str, field: str, value: str):
        message = f"{resource_type} with {field} '{value}' already exists"
        super().__init__(message)
        self.resource_type = resource_type
        self.field = field
        self.value = value


class DatabaseError(DocumentServiceError):
    """Raised when a database operation fails."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error
