"""Karnataka-specific validation exceptions."""

from care_eaushadhi.api.validators.exceptions import ValidationError


class KarnatakaValidationError(ValidationError):
    """Karnataka-specific validation error."""
    
    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict | None = None,
        deployment: str = "Karnataka",
    ):
        """Initialize Karnataka validation error."""
        super().__init__(message, error_code or "KARNATAKA_VALIDATION_ERROR", details)
        self.deployment = deployment


class InvalidInwardDateError(KarnatakaValidationError):
    """Invalid inward date (API returned null)."""
    
    def __init__(self, inward_date: str):
        super().__init__(
            message=f"Invalid inward date {inward_date}: API returned null",
            error_code="INVALID_INWARD_DATE",
            details={"inward_date": inward_date}
        )


class InvalidResponseTypeError(KarnatakaValidationError):
    """Response is not list or null."""
    
    def __init__(self, received_type: str):
        super().__init__(
            message=f"Expected list or null, got {received_type}",
            error_code="INVALID_RESPONSE_TYPE",
            details={"expected": "list or null", "received": received_type}
        )


class ItemValidationError(KarnatakaValidationError):
    """Item validation failed."""
    
    def __init__(self, item_index: int, error_message: str):
        super().__init__(
            message=f"Item {item_index} validation failed: {error_message}",
            error_code="ITEM_VALIDATION_FAILED",
            details={"item_index": item_index, "error": error_message}
        )