import datetime

from django.core.exceptions import ObjectDoesNotExist
from pydantic import UUID4, Field, ConfigDict
from rest_framework.exceptions import ValidationError

from care.emr.models.product import Product
from care.emr.models.product_knowledge import ProductKnowledge
from care.emr.models.supply_delivery import SupplyDelivery
from care.facility.models import Facility
from care.emr.resources.base import EMRResource

from care_eaushadhi.models.eaushadhi_inward_record_delivery import (
    EAushadhiInwardRecordDelivery,
)
from care_eaushadhi.models.eaushadhi_inward_record_item import (
    EAushadhiInwardRecordItem,
)
from care_eaushadhi.models.eaushadhi_inward_record_item_delivery import (
    EAushadhiInwardRecordItemDelivery,
    InwardRecordItemDeliveryStatus,
)


class RecordItemDeliveryReadSpec(EMRResource):

    __model__ = EAushadhiInwardRecordItemDelivery

    id: UUID4
    inward_record_id: UUID4
    delivery_order_id: UUID4
    facility_id: UUID4
    quantity_received: str
    status: str

    created_by: dict
    updated_by: dict

    created_date: datetime.datetime
    modified_date: datetime.datetime

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["inward_record_id"] = obj.inward_record_delivery.inward_record.external_id
        mapping["delivery_order_id"] = obj.inward_record_delivery.delivery_order.external_id
        mapping["facility_id"] = obj.facility.external_id
        mapping["quantity_received"] = str(obj.quantity_received)
        mapping["status"] = obj.status

        mapping["created_date"] = obj.created_date.isoformat(
        ) if obj.created_date else None
        mapping["modified_date"] = obj.modified_date.isoformat(
        ) if obj.modified_date else None
        cls.serialize_audit_users(mapping, obj)


class RecordItemDeliveryCreateSpec(EMRResource):

    __model__ = EAushadhiInwardRecordItemDelivery

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

    record_item_id: UUID4
    facility_id: UUID4
    supply_delivery_id: UUID4 | None
    record_delivery_id: UUID4
    product_id: UUID4
    product_knowledge_id: UUID4
    quantity_received: int | float

    def perform_extra_deserialization(self, is_update, obj):

        try:
            obj.facility = Facility.objects.get(external_id=self.facility_id)
        except ObjectDoesNotExist:
            raise ValidationError({"facility_id": ["Facility not found"]})

        try:
            obj.inward_record_item = EAushadhiInwardRecordItem.objects.get(
                external_id=self.record_item_id
            )
        except ObjectDoesNotExist:
            raise ValidationError(
                {"record_item_id": ["Record item not found"]})

        try:
            obj.inward_record_delivery = EAushadhiInwardRecordDelivery.objects.get(
                external_id=self.record_delivery_id
            )
        except ObjectDoesNotExist:
            raise ValidationError(
                {"record_delivery_id": ["Record delivery not found"]})

        try:
            obj.product = Product.objects.get(external_id=self.product_id)
        except ObjectDoesNotExist:
            raise ValidationError({"product_id": ["Product not found"]})

        try:
            obj.product_knowledge = ProductKnowledge.objects.get(
                external_id=self.product_knowledge_id
            )
        except ObjectDoesNotExist:
            raise ValidationError(
                {"product_knowledge_id": ["Product knowledge not found"]})

        if self.supply_delivery_id:
            try:
                obj.supply_delivery = SupplyDelivery.objects.get(
                    external_id=self.supply_delivery_id
                )
            except ObjectDoesNotExist:
                raise ValidationError(
                    {"supply_delivery_id": ["Supply delivery not found"]})
        else:
            obj.supply_delivery = None

        obj.quantity_received = self.quantity_received

        return obj


class RecordItemDeliveryUpdateSpec(EMRResource):

    __model__ = EAushadhiInwardRecordItemDelivery

    quantity_received: int | float | None = None
    status: str | None = None

    def perform_extra_deserialization(self, is_update, obj):

        if self.quantity_received is not None:
            obj.quantity_received = self.quantity_received

        if self.status is not None:
            valid_statuses = [choice[0]
                              for choice in InwardRecordItemDeliveryStatus.choices]
            if self.status not in valid_statuses:
                raise ValidationError({
                    "status": [f"Must be one of: {', '.join(valid_statuses)}"]
                })
            obj.status = self.status

        return obj
