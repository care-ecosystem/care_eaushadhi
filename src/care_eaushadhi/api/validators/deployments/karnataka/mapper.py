"""Karnataka eAushadhi response mapper.

Transforms validated InventoryItem to CARE internal format.
"""

from typing import Any
import logging
from datetime import date

from .schemas import InventoryItem

logger = logging.getLogger(__name__)


class KarnatakaMapper:
    """Maps validated Karnataka inventory items to CARE format.
    
    Context Requirements:
        - inward_date: Date object or ISO format string (YYYY-MM-DD) or DD/MM/YYYY
        - facility_id: UUID (optional, for logging)
    """

    @staticmethod
    def map_to_care_format(
        validated_item: InventoryItem,
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Map validated Karnataka inventory item to CARE internal format.

        Validates context, then transforms eAushadhi item format to CARE schema.
        All original eAushadhi data preserved in metadata JSONField.

        Args:
            validated_item: Successfully validated InventoryItem (from validator)
            context: Context dict with required 'inward_date' key
                Can be datetime.date, str (YYYY-MM-DD), or str (DD/MM/YYYY)

        Returns:
            Dictionary with keys ready for EAushadhiInwardRecordItem.objects.create():
        """
        inward_date = context.get("inward_date")
        
        if inward_date is None:
            raise ValueError(
                "Missing required context field: 'inward_date'. "
                "Expected: date object or ISO format string (YYYY-MM-DD)"
            )
        
        try:
            if isinstance(inward_date, str):
                # Try ISO format first (YYYY-MM-DD)
                if len(inward_date) == 10 and inward_date[4] == '-':
                    from datetime import datetime
                    inward_date = datetime.fromisoformat(inward_date).date()
                # Try DD/MM/YYYY format
                elif '/' in inward_date:
                    from datetime import datetime
                    inward_date = datetime.strptime(inward_date, "%d/%m/%Y").date()
                else:
                    raise ValueError(f"Unrecognized date format: {inward_date}")
            elif not isinstance(inward_date, date):
                raise TypeError(f"Expected date or str, got {type(inward_date).__name__}")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid inward_date: {e}")


        batch_number = validated_item.batch_number.strip() if validated_item.batch_number else ""
        if not batch_number:
            raise ValueError(
                f"Batch number cannot be empty for item {validated_item.inwardno}. "
                "eAushadhi API returned empty or whitespace-only batch number."
            )

        drug_id = validated_item.drug_id.strip() if validated_item.drug_id else ""
        if not drug_id:
            raise ValueError(f"Drug ID cannot be empty for item {validated_item.inwardno}")

        warehouse_name = validated_item.warehouse_name.strip() if validated_item.warehouse_name else ""
        if not warehouse_name:
            raise ValueError(
                f"Warehouse name cannot be empty for item {validated_item.inwardno}"
            )

        logger.debug(
            "Mapping item to CARE format | inwardno=%s drug_id=%s batch=%s",
            validated_item.inwardno,
            drug_id,
            batch_number,
        )

        mapped = {
            "eaushadhi_inwardno": validated_item.inwardno,
            "eaushadhi_institution_id": validated_item.instituteid,
            "eaushadhi_warehouse_name": warehouse_name,
            "quantity_in_units": validated_item.quantity_in_units,
            "quantity_in_pack": validated_item.quantity_in_pack,
            "unit_pack": validated_item.unit_pack,
            "available_quantity": validated_item.available_quantity,
            "is_expired": validated_item.is_expired,
            "metadata": {
                "sl_no": validated_item.sl_no,
                "drug_id": drug_id,
                "batch_number": batch_number,                
                "mfg_date": validated_item.mfg_date.isoformat(),
                "exp_date": validated_item.exp_date.isoformat(),
                "receipt_date": validated_item.receipt_date.isoformat(),                
                "drug_name": validated_item.drug_name.strip(),
                "dose": validated_item.dose.strip(),                
                "institute_name": validated_item.institute_name.strip(),
                "institute_type": validated_item.institute_type.value,
                "warehouse_name": warehouse_name,                
                "not_of_standard": validated_item.not_of_standard.value,
                
                "source_api": "eAushadhi",
                "inward_date": inward_date.isoformat(),
            },
        }

        logger.debug(
            "Item mapped successfully | inwardno=%s units=%d quantity_in_pack=%d",
            validated_item.inwardno,
            validated_item.quantity_in_units,
            validated_item.quantity_in_pack,
        )

        return mapped