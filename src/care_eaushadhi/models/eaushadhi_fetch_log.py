from django.db import models

from care.emr.models.base import EMRBaseModel
from care.facility.models import Facility

class FetchTriggeredBy(models.TextChoices):
    USER = "USER"
    CRON = "CRON"
    RETRY = "RETRY"

class FetchStatus(models.TextChoices):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"

class EAushadhiFetchLog(EMRBaseModel):
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name="eaushadhi_fetch_logs"
    )
    inward_date = models.DateField()
    triggered_by = models.CharField(
        choices=FetchTriggeredBy.choices,
        default=FetchTriggeredBy.USER,
        max_length=20
    )
    fetch_status = models.CharField(
        choices=FetchStatus.choices,
        default=FetchStatus.PENDING,
        max_length=20
    )
    http_status_code = models.PositiveIntegerField(null=True, blank=True)
    error_code = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    error_detail = models.TextField(blank=True, null=True)
    response_payload = models.JSONField(null=True, blank=True)
    api_response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    total_items_in_response = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "E-Aushadhi Fetch Logs"
        indexes = [
            models.Index(
                fields=["facility", "inward_date", "-created_date"],
                name="idx_facility_inward_date_created"
            )
        ]

    def __str__(self):
        return f"Fetch Log - {self.facility.name} - {self.inward_date}"
