from django.db import models

from care.emr.models.base import EMRBaseModel

from care_eaushadhi.models.eaushadhi_fetch_log import EAushadhiFetchLog
from care_eaushadhi.models.eaushadhi_inward_record import EAushadhiInwardRecord

class RecordItemStatus(models.TextChoices):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    EXPIRED = "EXPIRED"

class EAushadhiInwardRecordItem(EMRBaseModel):
    inward_record = models.ForeignKey(
        EAushadhiInwardRecord,
        on_delete=models.CASCADE,
        related_name="items"
    )
    inward_no = models.CharField(max_length=255)
    drug_id = models.CharField(max_length=255)
    drug_name = models.CharField(max_length=500)
    batch_no = models.CharField(max_length=255)
    manufactured_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    receipt_date = models.DateField(null=True, blank=True)
    unit_pack = models.DecimalField(max_digits=10, decimal_places=2)
    unit_pack_raw = models.TextField(blank=True, null=True)
    dose = models.CharField(max_length=255, blank=True)
    quantity_in_units = models.DecimalField(max_digits=12, decimal_places=2)
    quantity_received_current = models.DecimalField(max_digits=12, decimal_places=2)
    quantity_received_initial = models.DecimalField(max_digits=12, decimal_places=2)
    warehouse_name = models.CharField(max_length=255)
    status = models.CharField(
        choices=RecordItemStatus.choices,
        default=RecordItemStatus.ACTIVE,
        max_length=20
    )
    initial_fetch_log = models.ForeignKey(
        EAushadhiFetchLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items_initial_fetch"
    )
    current_fetch_log = models.ForeignKey(
        EAushadhiFetchLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items_current_fetch"
    )

    class Meta:
        verbose_name_plural = "E-Aushadhi Record Items"
        constraints = [
            models.UniqueConstraint(
                fields=["inward_record", "inward_no", "drug_id", "batch_no"],
                name="unique_inward_drug_batch"
            )
        ]

    def __str__(self):
        return f"{self.drug_name} - {self.batch_no}"
