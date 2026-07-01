import datetime
from pydantic import UUID4

from care.emr.resources.base import EMRResource

from care_eaushadhi.models.eaushadhi_inward_record import EAushadhiInwardRecord, SyncStatus
from care_eaushadhi.api.specs.inward_record_item import InwardRecordItemReadSpec
from care_eaushadhi.api.specs.inward_record_delivery import InwardRecordDeliveryReadSpec

class InwardRecordListSpec(EMRResource):
    __model__ = EAushadhiInwardRecord
    __exclude__ = []

    id: UUID4 | None = None
    meta: dict | None = None
    facility_id: UUID4 | None = None
    inward_date: datetime.date | None = None
    sync_status: SyncStatus | None = None
    last_successful_fetch_log_id: UUID4 | None = None
    last_attempted_fetch_log_id: UUID4 | None = None
    items_initial_count: int = 0
    items_current_count: int = 0
    created_by: dict | None = None
    updated_by: dict | None = None
    created_date: datetime.datetime | None = None
    modified_date: datetime.datetime | None = None

    def to_json(self):
        return self.model_dump(mode="json")

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["meta"] = obj.meta if obj.meta else {}
        mapping["facility_id"] = obj.facility.external_id if obj.facility else None
        mapping["last_successful_fetch_log_id"] = (
            obj.last_successful_fetch_log.external_id
            if obj.last_successful_fetch_log
            else None
        )
        mapping["last_attempted_fetch_log_id"] = (
            obj.last_attempted_fetch_log.external_id
            if obj.last_attempted_fetch_log
            else None
        )
        cls.serialize_audit_users(mapping, obj)


class InwardRecordRetrieveSpec(InwardRecordListSpec):
    items: dict = {"count": 0, "results": []}
    deliveries: list[dict] = []
    meta: dict | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj, *args, items=None, **kwargs):
        super().perform_extra_serialization(mapping, obj, *args, **kwargs)
        mapping["items"] = items if items is not None else {"count": 0, "results": []}
        mapping["deliveries"] = [
            InwardRecordDeliveryReadSpec.serialize(d).to_json()
            for d in obj.deliveries.all()
        ]
