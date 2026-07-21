class DomainError(Exception):
    """Base class for domain-layer errors across all modules."""


class NotFoundError(DomainError):
    """Raised when a requested aggregate does not exist."""


class ConflictError(DomainError):
    """Raised when an operation violates a business rule."""
