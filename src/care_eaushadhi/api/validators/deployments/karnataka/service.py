"""Karnataka eAushadhi validation and mapping service.

Orchestrates the complete pipeline:
1. Validate raw response → InventoryItem objects
2. Map to CARE format → dict for database
"""

from typing import Any
import logging

from .validator import KarnatakaValidator
from .mapper import KarnatakaMapper

logger = logging.getLogger(__name__)


class KarnatakaResponseService:
    """Service for validating and mapping Karnataka eAushadhi responses."""

    def __init__(self):
        """Initialize service with validator and mapper."""
        self.validator = KarnatakaValidator()
        self.mapper = KarnatakaMapper()

    def process_response(
        self,
        raw_response: Any,
        context: dict[str, Any]
    ) -> tuple[list[dict], list[dict]]:
        """Process raw API response through validation and mapping.

        Args:
            raw_response: Raw response from eAushadhi API
            context: Context dict (inward_date, facility_id, etc.)

        Returns:
            Tuple of (mapped_items, validation_errors)
            - mapped_items: List of dicts ready for CARE database
            - validation_errors: List of error dicts with details
        """
        logger.info(
            "Starting response processing for Karnataka | "
            "deployment=%s inward_date=%s",
            self.validator.config.deployment_name,
            context.get("inward_date", "unknown")
        )

        validation_errors = []
        mapped_items = []

        try:
            # Stage 1: Validate
            logger.debug("Stage 1: Validating response")
            validated_items = self.validator.validate(raw_response, context)
            logger.debug("Validation complete: %d items validated", len(validated_items))

            # Stage 2: Map
            logger.debug("Stage 2: Mapping to CARE format")
            for idx, item in enumerate(validated_items):
                try:
                    mapped = self.mapper.map_to_care_format(item, context)
                    mapped_items.append(mapped)
                except Exception as e:
                    logger.warning(
                        "Mapping failed for item %d | error=%s",
                        idx,
                        str(e)
                    )
                    validation_errors.append({
                        "error_code": "MAPPING_ERROR",
                        "message": f"Mapping failed for item {idx}: {str(e)}",
                        "details": {"item_index": idx}
                    })

            logger.info(
                "Processing complete | mapped=%d errors=%d",
                len(mapped_items),
                len(validation_errors)
            )

            return mapped_items, validation_errors

        except Exception as e:
            logger.exception("Error processing response")
            return [], [{
                "error_code": "PROCESSING_ERROR",
                "message": str(e),
                "details": {}
            }]