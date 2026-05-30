from django.db import models

from care.emr.models.base import EMRBaseModel
from care.facility.models import Facility

from care_eaushadhi.models import EAushadhiFetchLog

class SyncStatus(models.TextChoices):
    NEVER_SYNCED = "NEVER_SYNCED"
    FRESH = "FRESH"
    STALE = "STALE"
    SYNCING = "SYNCING"
    FAILED = "FAILED"

class EAushadhiInwardRecord(EMRBaseModel):
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name="eaushadhi_inward_records"
    )
    inward_date = models.DateField()
    sync_status = models.CharField(
        choices=SyncStatus.choices,
        default=SyncStatus.NEVER_SYNCED,
        max_length=20
    )
    last_successful_fetch_log = models.ForeignKey(
        EAushadhiFetchLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="successful_inward_records"
    )
    last_attempted_fetch_log = models.ForeignKey(
        EAushadhiFetchLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attempted_inward_records"
    )
    items_initial_count = models.PositiveIntegerField(null=True, blank=True)
    items_current_count = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "E-Aushadhi Inward Records"
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "inward_date"],
                name="unique_facility_inward_date"
            )
        ]

    def __str__(self):
        return f"Inward Record - {self.facility.name} - {self.inward_date}"
