import datetime
from pydantic import UUID4

from care.emr.resources.base import EMRResource

from care_eaushadhi.models.eaushadhi_inward_record import EAushadhiInwardRecord, SyncStatus
from care_eaushadhi.api.specs.inward_record_item import InwardRecordItemReadSpec
from care_eaushadhi.api.specs.inward_record_item_delivery import InwardRecordItemDeliveryReadSpec


class InwardRecordListSpec(EMRResource):
    __model__ = EAushadhiInwardRecord
    __exclude__ = []

    id: UUID4 | None = None
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

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
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
    items: list[dict] = []
    deliveries: list[dict] = []

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        super().perform_extra_serialization(mapping, obj)
        mapping["items"] = [
            InwardRecordItemReadSpec.serialize(item).to_json()
            for item in obj.items.prefetch_related("item_deliveries").all()
        ]
        mapping["deliveries"] = [
            InwardRecordItemDeliveryReadSpec.serialize(d).to_json()
            for d in obj.deliveries.all()
        ]
