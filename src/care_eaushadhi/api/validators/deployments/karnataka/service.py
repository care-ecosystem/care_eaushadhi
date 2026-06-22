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

logger = logging.getLogger(__name__)


class ProcessingMetrics(NamedTuple):
    """Metrics from response processing."""
    total_items: int
    items_mapped: int
    items_failed: int
    error_rate: float  # 0.0 to 1.0
    duration_ms: float
    items_per_second: float


class KarnatakaResponseService:
    """Service for validating and mapping Karnataka eAushadhi responses.
    
    Configuration:
        - MAX_ITEMS_PER_REQUEST: Maximum items allowed in single response (default: 10000)
        - MAX_ALLOWED_ERROR_PERCENTAGE: Reject batch if error rate exceeds this (default: 10)
    
    Error Handling:
        - Collects all errors but allows partial success (partial_success mode)
        - Returns both mapped items and validation errors to caller
        - Rejects entire batch if error percentage exceeds threshold
    """

    # Configuration
    MAX_ITEMS_PER_REQUEST = 10000
    MAX_ALLOWED_ERROR_PERCENTAGE = 10  # Reject batch if >10% errors

    def __init__(self):
        """Initialize service with validator and mapper."""
        self.validator = KarnatakaValidator()
        self.mapper = KarnatakaMapper()

    def process_response(
        self,
        raw_response: Any,
        context: dict[str, Any]
    ) -> tuple[list[dict], list[dict], ProcessingMetrics]:
        """Process raw API response through validation and mapping.

        Complete pipeline:
        1. Validate raw response structure and items
        2. Map each validated item to CARE format
        3. Check error threshold
        4. Return results with metrics

        Args:
            raw_response: Raw response from eAushadhi API
                Can be: list of items, empty list [], or null/None
            context: Context dict with at minimum:
                - inward_date: Date object or ISO string

        Returns:
            Tuple of:
            - mapped_items: List of dicts ready for CARE database (empty if batch rejected)
            - validation_errors: List of error dicts with details
            - metrics: ProcessingMetrics with timing and statistics

        Raises:
            ValidationError: Only if validation pipeline itself fails
                (e.g., invalid response type not caught in validator)

        Example:
            >>> service = KarnatakaResponseService()
            >>> response = [{"Sl_No": 1, ...}, {"Sl_No": 2, ...}]
            >>> items, errors, metrics = service.process_response(
            ...     response,
            ...     {"inward_date": "2026-05-04"}
            ... )
            >>> print(f"Mapped {metrics.items_mapped} items, {metrics.items_failed} errors")
        """
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
            # ================================================================
            # STAGE 1: VALIDATE
            # ================================================================
            logger.debug("Stage 1: Validating raw response from eAushadhi API")
            
            validated_items = self.validator.validate(raw_response, context)
            
            logger.debug(
                "Validation complete | total_items=%d",
                len(validated_items)
            )

            # ================================================================
            # STAGE 2: CHECK RESPONSE SIZE
            # ================================================================
            if len(validated_items) > self.MAX_ITEMS_PER_REQUEST:
                error_msg = (
                    f"Response contains {len(validated_items)} items, "
                    f"exceeds limit of {self.MAX_ITEMS_PER_REQUEST}"
                )
                logger.warning("Response size check failed | %s", error_msg)
                
                elapsed = time.time() - start_time
                return [], [{
                    "error_code": "RESPONSE_SIZE_EXCEEDED",
                    "message": error_msg,
                    "details": {
                        "item_count": len(validated_items),
                        "max_allowed": self.MAX_ITEMS_PER_REQUEST,
                    }
                }], ProcessingMetrics(
                    total_items=len(validated_items),
                    items_mapped=0,
                    items_failed=0,
                    error_rate=1.0,
                    duration_ms=elapsed * 1000,
                    items_per_second=0,
                )

            # ================================================================
            # STAGE 3: MAP EACH ITEM
            # ================================================================
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

            # ================================================================
            # STAGE 4: CHECK ERROR THRESHOLD
            # ================================================================
            total_processed = len(mapped_items) + len(validation_errors)
            
            if total_processed > 0:
                error_rate = len(validation_errors) / total_processed
                error_percentage = error_rate * 100
                
                logger.info(
                    "Mapping complete | mapped=%d errors=%d error_rate=%.1f%%",
                    len(mapped_items),
                    len(validation_errors),
                    error_percentage,
                )
                
                # Reject batch if error rate exceeds threshold
                if error_rate > (self.MAX_ALLOWED_ERROR_PERCENTAGE / 100):
                    logger.error(
                        "Batch rejected: error rate %.1f%% exceeds threshold %.1f%% | "
                        "mapped=%d errors=%d",
                        error_percentage,
                        self.MAX_ALLOWED_ERROR_PERCENTAGE,
                        len(mapped_items),
                        len(validation_errors),
                    )
                    
                    # Clear mapped items - reject entire batch
                    batch_errors = validation_errors.copy()
                    mapped_items = []
                    
                    batch_errors.insert(0, {
                        "error_code": "BATCH_ERROR_THRESHOLD_EXCEEDED",
                        "message": (
                            f"Batch rejected: error rate {error_percentage:.1f}% "
                            f"exceeds threshold {self.MAX_ALLOWED_ERROR_PERCENTAGE}%"
                        ),
                        "details": {
                            "total_items": total_processed,
                            "error_count": len(validation_errors),
                            "error_rate": error_rate,
                        }
                    })
                    
                    validation_errors = batch_errors
            else:
                error_rate = 0.0

            # ================================================================
            # STAGE 5: RETURN RESULTS WITH METRICS
            # ================================================================
            elapsed = time.time() - start_time
            items_per_second = len(validated_items) / elapsed if elapsed > 0 else 0
            
            metrics = ProcessingMetrics(
                total_items=len(validated_items),
                items_mapped=len(mapped_items),
                items_failed=len(validation_errors),
                error_rate=error_rate,
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
                error_rate=1.0,
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
                error_rate=1.0,
                duration_ms=elapsed * 1000,
                items_per_second=0,
            )
