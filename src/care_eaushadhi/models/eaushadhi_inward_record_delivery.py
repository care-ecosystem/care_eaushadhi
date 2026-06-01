from django.db import models

from care.emr.models.base import EMRBaseModel
from care.emr.models.supply_delivery import DeliveryOrder

from care_eaushadhi.models.eaushadhi_inward_record import EAushadhiInwardRecord

class EAushadhiInwardRecordDelivery(EMRBaseModel):
    inward_record = models.ForeignKey(
        EAushadhiInwardRecord,
        on_delete=models.CASCADE,
        related_name="deliveries"
    )
    delivery_order = models.OneToOneField(
        DeliveryOrder,
        on_delete=models.PROTECT,
        unique=True,
        related_name="eaushadhi_record_delivery"
    )

    class Meta:
        verbose_name_plural = "E-Aushadhi Record Deliveries"
        constraints = [
            models.UniqueConstraint(
                fields=["delivery_order"],
                name="uniq_delivery_order"
            )
        ]
        indexes = [
            models.Index(
                fields=["inward_record", "deleted"],
                name="idx_inward_record_deleted"
            )
        ]

    def __str__(self):
        return f"Delivery - {self.inward_record} - {self.delivery_order}"
