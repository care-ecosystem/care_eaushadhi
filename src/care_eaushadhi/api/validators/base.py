"""Abstract base validator for eAushadhi API responses."""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any
import logging

from .exceptions import ValidationError

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

    def validate_and_map(
        self,
        raw_response: Any,
        context: dict[str, Any]
    ) -> tuple[list[M], list[ValidationError]]:
        """Execute complete validation and mapping pipeline.

        This is the main entry point for processing eAushadhi responses.
        It orchestrates the full pipeline:
        1. Validates raw response structure and content
        2. Maps validated data to CARE internal format
        3. Collects all validation errors

        Args:
            raw_response: Raw JSON/dict response from eAushadhi API
            context: Additional context (facility_id, inward_date, etc.)

        Returns:
            Tuple of (validated_and_mapped_items, validation_errors)
            - validated_and_mapped_items: List of successfully validated and mapped items
            - validation_errors: List of ValidationError objects encountered

        Note:
            Partial success is possible: items with validation errors are excluded
            from the returned list, but processing continues for remaining items.
            All errors are collected in the second element of the tuple.
        """
        validation_errors = []
        mapped_items = []

        try:
            logger.info(
                "Starting validation pipeline for %s",
                self.config.deployment_name,
            )

            # Stage 1: Validate raw response
            validated_items = self.validate(raw_response, context)
            logger.debug(
                "Validation stage complete: %d items validated",
                len(validated_items),
            )

            # Stage 2: Map validated items to CARE format
            for idx, item in enumerate(validated_items):
                try:
                    mapped_item = self.map_to_care_format(item, context)
                    mapped_items.append(mapped_item)
                except ValidationError as e:
                    logger.warning(
                        "Mapping error for item %d: %s",
                        idx,
                        e.to_dict(),
                    )
                    validation_errors.append(e)
                except Exception as e:
                    logger.exception(
                        "Unexpected error mapping item %d",
                        idx,
                    )
                    error = ValidationError(
                        message=f"Unexpected mapping error for item {idx}: {str(e)}",
                        error_code="MAPPING_ERROR",
                        details={
                            "item_index": idx,
                            "exception_type": type(e).__name__,
                        },
                    )
                    validation_errors.append(error)

            logger.info(
                "Pipeline complete: %d items mapped, %d errors",
                len(mapped_items),
                len(validation_errors),
            )

            return mapped_items, validation_errors

        except ValidationError as e:
            logger.warning(
                "Validation failed: %s",
                e.to_dict(),
            )
            return [], [e]
        except Exception as e:
            logger.exception(
                "Unexpected error in validation pipeline"
            )
            error = ValidationError(
                message=f"Unexpected error: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                details={"exception_type": type(e).__name__},
            )
            return [], [error]