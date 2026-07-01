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
    delivery_order_id: UUID4 | None = None
    product_id: UUID4 | None = None
    product_knowledge_id: UUID4 | None = None
    quantity_received: int = 0
    status: InwardRecordItemDeliveryStatus | None = None
    deleted: bool = False

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id

        if obj.supply_delivery:
            mapping["supply_delivery_id"] = obj.supply_delivery.external_id

        if obj.inward_record_delivery:
            mapping["record_delivery_id"] = obj.inward_record_delivery.external_id
            if obj.inward_record_delivery.delivery_order:
                mapping["delivery_order_id"] = (
                    obj.inward_record_delivery.delivery_order.external_id
                )

        if obj.product:
            mapping["product_id"] = obj.product.external_id

        if obj.product_knowledge:
            mapping["product_knowledge_id"] = obj.product_knowledge.external_id

