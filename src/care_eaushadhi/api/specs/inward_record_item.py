import datetime
from enum import Enum
from pydantic import UUID4

from care.emr.resources.base import EMRResource

from care_eaushadhi.models.eaushadhi_inward_record_item import EAushadhiInwardRecordItem
from care_eaushadhi.api.specs.inward_record_item_delivery import InwardRecordItemDeliveryReadSpec

class RecordItemStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    EXPIRED = "EXPIRED"

class InwardRecordItemReadSpec(EMRResource):
    __model__ = EAushadhiInwardRecordItem
    __exclude__ = []

    id: UUID4 | None = None
    inward_no: str | None = None
    drug_id: str | None = None
    drug_name: str | None = None
    batch_no: str | None = None
    manufactured_date: datetime.date | None = None
    expiry_date: datetime.date | None = None
    receipt_date: datetime.date | None = None
    unit_pack: int | None = None
    unit_pack_raw: str | None = None
    dose: str | None = None
    quantity_in_units: int = 0
    quantity_received_current: int = 0
    quantity_received_initial: int = 0
    warehouse_name: str | None = None
    status: RecordItemStatus | None = None
    created_date: datetime.datetime | None = None
    modified_date: datetime.datetime | None = None
    item_deliveries: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["item_deliveries"] = [
            InwardRecordItemDeliveryReadSpec.serialize(d).to_json()
            for d in obj.item_deliveries.all()
        ]
