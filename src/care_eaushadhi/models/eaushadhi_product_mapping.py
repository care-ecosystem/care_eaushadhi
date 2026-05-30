from django.db import models
from care.emr.models.base import EMRBaseModel
from care.facility.models import Facility
from care.emr.models import ProductKnowledge

class EauShadhiProductMapping(EMRBaseModel):
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="eaushadhi_product_mappings",
        help_text="Facility-specific or global if null"
    )
    eaushadhi_drug_id = models.CharField(max_length=255)
    eaushadhi_drug_name = models.CharField(max_length=500)
    product_knowledge = models.ForeignKey(
        ProductKnowledge,
        on_delete=models.PROTECT,
        related_name="eaushadhi_mappings"
    )
    usage_count = models.IntegerField(default=0)
    last_used_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "E-Aushadhi Product Mappings"
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "eaushadhi_drug_id"],
                name="uniq_facility_drug_id"
            )
        ]

    def __str__(self):
        facility_name = self.facility.name if self.facility else "Global"
        return f"{facility_name} - {self.eaushadhi_drug_name}"
