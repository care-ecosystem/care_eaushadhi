from django.db import models

from care.emr.models.base import EMRBaseModel
from care.emr.models.supply_delivery import SupplyDelivery
from care.emr.models.product import Product
from care.emr.models.product_knowledge import ProductKnowledge
from care.facility.models import Facility

from care_eaushadhi.models.eaushadhi_inward_record_delivery import EAushadhiInwardRecordDelivery
from care_eaushadhi.models.eaushadhi_inward_record_item import EAushadhiInwardRecordItem

class InwardRecordItemDeliveryStatus(models.TextChoices):
    ACTIVE = "ACTIVE"
    REVERSED = "REVERSED"

class EAushadhiInwardRecordItemDelivery(EMRBaseModel):
    inward_record_item = models.OneToOneField(
        EAushadhiInwardRecordItem,
        on_delete=models.CASCADE,
        unique=True,
        related_name="consumption"
    )
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name="eaushadhi_item_consumptions"
    )
    supply_delivery = models.ForeignKey(
        SupplyDelivery,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eaushadhi_consumptions"
    )
    inward_record_delivery = models.ForeignKey(
        EAushadhiInwardRecordDelivery,
        on_delete=models.CASCADE,
        related_name="item_consumptions"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="eaushadhi_consumptions"
    )
    product_knowledge = models.ForeignKey(
        ProductKnowledge,
        on_delete=models.PROTECT,
        related_name="eaushadhi_consumptions"
    )
    quantity_received = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Snapshot at consumption time"
    )
    status = models.CharField(
        choices=InwardRecordItemDeliveryStatus.choices,
        default=InwardRecordItemDeliveryStatus.ACTIVE,
        max_length=20
    )

    class Meta:
        verbose_name_plural = "E-Aushadhi Inward Record Item"
        constraints = [
            models.UniqueConstraint(
                fields=["inward_record_item"],
                name="uniq_inward_record_item"
            )
        ]

    def __str__(self):
        return f"Inward Record Item Delivery - {self.inward_record_item}"
