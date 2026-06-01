from django.db import models

from care.emr.models.base import EMRBaseModel
from care.facility.models import Facility

class EAushadhiInstituteMapping(EMRBaseModel):
    facility = models.OneToOneField(
        Facility,
        on_delete=models.PROTECT,
        unique=True,
        related_name="eaushadhi_institute_mapping"
    )
    eaushadhi_institute_id = models.CharField(max_length=255)
    schema_version = models.CharField(max_length=50)
    credentials_ref = models.CharField(max_length=255, help_text="Vault reference for upstream auth")

    class Meta:
        verbose_name_plural = "E-Aushadhi Institute Mappings"
        constraints = [
            models.UniqueConstraint(
                fields=["facility"],
                name="uniq_facility_mapping"
            )
        ]

    def __str__(self):
        return f"E-Aushadhi Mapping - {self.facility.name}"
