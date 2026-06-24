import datetime

from django.core.exceptions import ObjectDoesNotExist
from pydantic import UUID4
from rest_framework.exceptions import ValidationError

from care.emr.models.supply_delivery import DeliveryOrder
from care.emr.resources.base import EMRResource

from care.facility.models import Facility

from care_eaushadhi.models.eaushadhi_inward_record import (
    EAushadhiInwardRecord,
)
from care_eaushadhi.models.eaushadhi_inward_record_delivery import (
    EAushadhiInwardRecordDelivery,
)


class RecordDeliveryReadSpec(EMRResource):
    __model__ = EAushadhiInwardRecordDelivery

    id: UUID4
    inward_record_id: UUID4
    delivery_order_id: UUID4
    facility_id: UUID4

    created_by: dict
    updated_by: dict

    created_date: datetime.datetime
    modified_date: datetime.datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["inward_record_id"] = obj.inward_record.external_id
        mapping["delivery_order_id"] = obj.delivery_order.external_id
        mapping["facility_id"] = obj.inward_record.facility.external_id

        cls.serialize_audit_users(mapping, obj)


class RecordDeliveryCreateSpec(EMRResource):
    __model__ = EAushadhiInwardRecordDelivery

    __exclude__ = [
        "id",
        "external_id",
        "created_by",
        "updated_by",
        "created_date",
        "modified_date",
        "deleted",
        "history",
    ]

    inward_record_id: UUID4
    facility_id: UUID4
    delivery_order_id: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        try:
            inward_record = EAushadhiInwardRecord.objects.get(
                external_id=self.inward_record_id
            )
        except ObjectDoesNotExist:
            raise ValidationError("Inward record not found")

        try:
            facility = Facility.objects.get(
                external_id=self.facility_id
            )
        except ObjectDoesNotExist:
            raise ValidationError("Facility not found")

        try:
            delivery_order = DeliveryOrder.objects.get(
                external_id=self.delivery_order_id
            )
        except ObjectDoesNotExist:
            raise ValidationError("Delivery order not found")

        if inward_record.facility_id != facility.id:
            raise ValidationError(
                "facility_id does not match the inward_record's facility"
            )

        obj.inward_record = inward_record
        obj.delivery_order = delivery_order

        return obj