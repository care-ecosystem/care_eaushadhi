"""Karnataka eAushadhi response validator.

Handles validation of raw API responses.
Maps to InventoryItem Pydantic models.
"""

from typing import Any
import logging

from care_eaushadhi.api.validators.base import BaseResponseValidator
from care_eaushadhi.api.validators.exceptions import ValidationError

from .schemas import InventoryItem
from .exceptions import (
    InvalidInwardDateError,
    InvalidResponseTypeError,
    ItemValidationError,
)

logger = logging.getLogger(__name__)


class KarnatakaValidator(BaseResponseValidator[InventoryItem, InventoryItem]):
    """Validator for Karnataka eAushadhi API responses.
    
    Validates raw API response and returns Pydantic InventoryItem objects.
    Handles all three response patterns:
    - Valid date with items: [{ item1 }, { item2 }, ...]
    - Valid date, no items: []
    - Invalid date (e.g., 31/04/2026): null
    """

    class Config:
        deployment_name = "Karnataka"
        api_version = "1.0"

    def validate(
        self,
        raw_response: Any,
        context: dict[str, Any]
    ) -> list[InventoryItem]:
        """Validate raw Karnataka eAushadhi API response.
        
        Args:
            raw_response: Raw response from eAushadhi API
            context: Context dict (should include inward_date)
            
        Returns:
            List of validated InventoryItem objects
            
        Raises:
            ValidationError: On any validation failure
        """
        inward_date = context.get("inward_date", "unknown")

        logger.info(
            "Starting validation for Karnataka eAushadhi response | "
            "inward_date=%s response_type=%s",
            inward_date,
            type(raw_response).__name__,
        )

        # Handle null response (invalid date in API)
        if raw_response is None:
            logger.warning(
                "Received null response from eAushadhi API | inward_date=%s",
                inward_date,
            )
            raise InvalidInwardDateError(str(inward_date))

        # Handle non-list response
        if not isinstance(raw_response, list):
            logger.error(
                "Invalid response type | expected=list received=%s",
                type(raw_response).__name__,
            )
            raise InvalidResponseTypeError(type(raw_response).__name__)

        # Handle empty list (valid date, no items)
        if not raw_response:
            logger.info(
                "Received empty list from eAushadhi API | inward_date=%s",
                inward_date,
            )
            return []

        # Validate each item
        validated_items: list[InventoryItem] = []

        for idx, raw_item in enumerate(raw_response):
            try:
                logger.debug(
                    "Validating item %d of %d | inward_date=%s",
                    idx + 1,
                    len(raw_response),
                    inward_date,
                )

                # Use Pydantic to validate and normalize
                validated_item = InventoryItem.model_validate(raw_item)
                validated_items.append(validated_item)

                logger.debug(
                    "Item %d validated successfully | inwardno=%s",
                    idx,
                    validated_item.inwardno,
                )

            except ValueError as e:
                logger.warning(
                    "Item %d validation failed | error=%s",
                    idx,
                    str(e)[:100],
                )
                raise ItemValidationError(idx, str(e))
            except Exception as e:
                logger.exception("Unexpected error validating item %d", idx)
                raise ItemValidationError(idx, f"{type(e).__name__}: {str(e)}")

        logger.info(
            "Validation complete | inward_date=%s total=%d validated=%d",
            inward_date,
            len(raw_response),
            len(validated_items),
        )

        return validated_items

    def map_to_care_format(
        self,
        validated_item: InventoryItem,
        context: dict[str, Any]
    ) -> InventoryItem:
        """For abstract contract - returns validated item as-is.
        
        Actual mapping happens in mapper.py
        """
        return validated_item