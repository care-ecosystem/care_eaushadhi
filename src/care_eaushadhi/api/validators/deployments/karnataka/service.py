"""Karnataka eAushadhi validation and mapping service.

Orchestrates the complete pipeline:
1. Validate raw response → InventoryItem objects
2. Map to CARE format → dict for database

Pipeline Statistics:
- Input: Raw API response (list, empty list, or null)
- Output: Tuple of (mapped_items, validation_errors, metrics)
- Metrics: Item count, error count, processing time
"""

from typing import Any, NamedTuple
import logging
import time

from .validator import KarnatakaValidator
from .mapper import KarnatakaMapper
from care_eaushadhi.api.validators.exceptions import ValidationError
from care_eaushadhi.settings import plugin_settings as settings

logger = logging.getLogger(__name__)


class ProcessingMetrics(NamedTuple):
    """Metrics from response processing."""
    total_items: int
    items_mapped: int
    items_failed: int
    # error_rate: float  # 0.0 to 1.0
    duration_ms: float
    items_per_second: float


class KarnatakaResponseService:

    def __init__(self):
        """Initialize service with validator and mapper."""
        self.validator = KarnatakaValidator()
        self.mapper = KarnatakaMapper()

    def process_response(
        self,
        raw_response: Any,
        context: dict[str, Any]
    ) -> tuple[list[dict], list[dict], ProcessingMetrics]:
        
        logger.info(
            "Starting response processing for Karnataka | "
            "deployment=%s inward_date=%s",
            self.validator.config.deployment_name,
            context.get("inward_date", "unknown")
        )

        # Track timing
        start_time = time.time()
        
        validation_errors = []
        mapped_items = []

        try:
            logger.debug("Stage 1: Validating raw response from eAushadhi API")
            
            validated_items = self.validator.validate(raw_response, context)
            
            logger.debug(
                "Validation complete | total_items=%d",
                len(validated_items)
            )

            logger.debug("Stage 3: Mapping %d items to CARE format", len(validated_items))
            
            for idx, item in enumerate(validated_items):
                try:
                    logger.debug(
                        "Mapping item %d/%d | inwardno=%s",
                        idx + 1,
                        len(validated_items),
                        item.inwardno
                    )
                    
                    mapped = self.mapper.map_to_care_format(item, context)
                    mapped_items.append(mapped)
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(
                        "Mapping failed for item %d/%d (inwardno=%s) | error=%s",
                        idx + 1,
                        len(validated_items),
                        getattr(item, 'inwardno', 'unknown'),
                        error_msg[:100],
                    )
                    
                    validation_errors.append({
                        "error_code": "MAPPING_ERROR",
                        "message": f"Item {idx} mapping failed: {error_msg}",
                        "details": {
                            "item_index": idx,
                            "inwardno": getattr(item, 'inwardno', None),
                        }
                    })

            elapsed = time.time() - start_time
            items_per_second = len(validated_items) / elapsed if elapsed > 0 else 0
            
            metrics = ProcessingMetrics(
                total_items=len(validated_items),
                items_mapped=len(mapped_items),
                items_failed=len(validation_errors),
                duration_ms=elapsed * 1000,
                items_per_second=items_per_second,
            )
            
            logger.info(
                "Processing complete | metrics=%r",
                metrics._asdict(),
            )
            
            return mapped_items, validation_errors, metrics

        except ValidationError as e:
            # Expected error from validator
            logger.error("Validation error | %s", e.to_dict())
            elapsed = time.time() - start_time
            return [], [e.to_dict()], ProcessingMetrics(
                total_items=0,
                items_mapped=0,
                items_failed=1,
                duration_ms=elapsed * 1000,
                items_per_second=0,
            )

        except Exception as e:
            # Unexpected error
            logger.exception("Unexpected error during processing")
            elapsed = time.time() - start_time
            return [], [{
                "error_code": "PROCESSING_ERROR",
                "message": f"Unexpected error: {str(e)[:200]}",
                "details": {"error_type": type(e).__name__}
            }], ProcessingMetrics(
                total_items=0,
                items_mapped=0,
                items_failed=1,
                duration_ms=elapsed * 1000,
                items_per_second=0,
            )
