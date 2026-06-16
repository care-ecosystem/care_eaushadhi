"""Karnataka eAushadhi response mapper.

Transforms validated InventoryItem to CARE internal format.
"""

from typing import Any
import logging

from .schemas import InventoryItem

logger = logging.getLogger(__name__)


class KarnatakaMapper:
    """Maps validated Karnataka inventory items to CARE format."""

    @staticmethod
    def map_to_care_format(
        validated_item: InventoryItem,
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Map validated Karnataka inventory item to CARE internal format.

        Args:
            validated_item: Successfully validated InventoryItem
            context: Context dict (inward_date, facility_id, etc.)

        Returns:
            Dictionary ready for EAushadhiInwardRecordItem.objects.create()
        """
        inward_date = context.get("inward_date")

        if not inward_date:
            raise ValueError("Missing required context: inward_date")

        logger.debug(
            "Mapping item to CARE format | inwardno=%s drug_id=%s",
            validated_item.inwardno,
            validated_item.drug_id,
        )

        # Extract common fields
        mapped = {
            "eaushadhi_inwardno": validated_item.inwardno,
            "eaushadhi_institution_id": validated_item.instituteid,
            "eaushadhi_warehouse_name": validated_item.warehouse_name,
            "quantity_in_units": validated_item.quantity_in_units,
            "quantity_in_pack": validated_item.quantity_in_pack,
            "unit_pack": validated_item.unit_pack,
            "available_quantity": validated_item.available_quantity,
            "is_expired": validated_item.is_expired,
            # Store all eAushadhi-specific data in metadata
            "metadata": {
                "batch_number": validated_item.batch_number,
                "mfg_date": validated_item.mfg_date.isoformat(),
                "exp_date": validated_item.exp_date.isoformat(),
                "receipt_date": validated_item.receipt_date.isoformat(),
                "drug_id": validated_item.drug_id,
                "drug_name": validated_item.drug_name,
                "dose": validated_item.dose,
                "not_of_standard": validated_item.not_of_standard.value,
                "institute_name": validated_item.institute_name,
                "institute_type": validated_item.institute_type.value,
                "warehouse_name": validated_item.warehouse_name,
                "sl_no": validated_item.sl_no,
            },
        }

        logger.debug(
            "Item mapped successfully | inwardno=%s",
            validated_item.inwardno,
        )

        return mapped