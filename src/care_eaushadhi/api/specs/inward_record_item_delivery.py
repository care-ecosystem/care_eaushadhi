import datetime
from pydantic import UUID4

from care.emr.resources.base import EMRResource

from care_eaushadhi.models.eaushadhi_inward_record_item_delivery import (
    EAushadhiInwardRecordItemDelivery,
    InwardRecordItemDeliveryStatus
)


class InwardRecordItemDeliveryReadSpec(EMRResource):
    __model__ = EAushadhiInwardRecordItemDelivery
    __exclude__ = []

    id: UUID4 | None = None
    supply_delivery_id: UUID4 | None = None
    record_delivery_id: UUID4 | None = None
    product_id: UUID4 | None = None
    product_knowledge_id: UUID4 | None = None
    quantity_received: int = 0
    status: InwardRecordItemDeliveryStatus | None = None
    deleted: bool = False
    created_by: dict | None = None
    updated_by: dict | None = None
    created_date: datetime.datetime | None = None
    modified_date: datetime.datetime | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        cls.serialize_audit_users(mapping, obj)
