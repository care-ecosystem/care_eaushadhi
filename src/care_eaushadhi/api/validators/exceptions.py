"""Validation exceptions for eAushadhi API responses."""

from typing import Any


class ValidationError(Exception):
    """Base exception for validation errors with error codes and context.
    
    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code for categorization
        details: Additional error context (field names, values, etc.)
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize validation error.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code for categorization
            details: Additional error context
        """
        self.message = message
        self.error_code = error_code or "VALIDATION_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Serialize error to dictionary for logging/API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }

    def __repr__(self) -> str:
        return f"ValidationError({self.error_code}: {self.message})"