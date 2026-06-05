import datetime
from pydantic import UUID4

from care.emr.resources.base import EMRResource

from care_eaushadhi.models.eaushadhi_inward_record_delivery import EAushadhiInwardRecordDelivery

class InwardRecordDeliveryReadSpec(EMRResource):
    __model__ = EAushadhiInwardRecordDelivery
    __exclude__ = []

    id: UUID4 | None = None
    inward_record_id: UUID4 | None = None
    delivery_order_id: UUID4 | None = None
    created_by: dict | None = None
    updated_by: dict | None = None
    created_date: datetime.datetime | None = None
    modified_date: datetime.datetime | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["inward_record_id"] = obj.inward_record.external_id
        cls.serialize_audit_users(mapping, obj)
