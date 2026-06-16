"""Abstract base validator for eAushadhi API responses."""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any
import logging

from care_eaushadhi.api.validators.exceptions import ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T")  # Type for validated data
M = TypeVar("M")  # Type for mapped data


class BaseResponseValidator(ABC, Generic[T, M]):
    """Abstract base class for eAushadhi API response validators.

    This class defines the contract that all state-specific validators must
    implement. Subclasses must implement two abstract methods:

    1. validate(): Perform structural and domain-specific validation
    2. map_to_care_format(): Transform validated data to CARE internal format

    The validate_and_map() method orchestrates the full pipeline.

    Type Parameters:
        T: Type of validated item (e.g., InventoryItem)
        M: Type of mapped item (e.g., dict for CARE database)
    """

    class Config:
        """Base configuration for validators."""
        deployment_name: str = "base"
        api_version: str = "1.0"

    def __init__(self):
        """Initialize validator."""
        self.config = self.Config()

    @abstractmethod
    def validate(
        self, 
        raw_response: Any, 
        context: dict[str, Any]
    ) -> list[T]:
        """Validate raw eAushadhi API response.

        This method must perform all structural and domain-specific validation.
        It should:
        1. Check response structure (null checks, type checks, etc.)
        2. Validate each item against deployment-specific rules
        3. Perform cross-field invariant checks
        4. Raise ValidationError on any failure

        Args:
            raw_response: Raw response from eAushadhi API (typically list or null)
            context: Additional context for validation (facility_id, inward_date, etc.)

        Returns:
            List of successfully validated objects (type T)

        Raises:
            ValidationError: On any validation failure (with details)
        """
        ...

    @abstractmethod
    def map_to_care_format(
        self, 
        validated_item: T, 
        context: dict[str, Any]
    ) -> M:
        """Map validated item to CARE internal format.

        This method receives a successfully validated item and transforms it
        to the format expected by CARE's inventory management system.

        Args:
            validated_item: Successfully validated item from validate()
            context: Deployment context (facility_id, inward_date, etc.)

        Returns:
            Mapped object ready for CARE database storage (type M)

        Raises:
            ValidationError: If mapping fails (invalid state, missing context, etc.)
        """
        ...

