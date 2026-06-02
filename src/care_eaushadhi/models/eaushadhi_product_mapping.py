from django.db import models
from django.db.models import Q
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
            # 1. Facility-specific uniqueness
            models.UniqueConstraint(
                fields=["facility", "eaushadhi_drug_id", "product_knowledge"],
                name="uniq_facility_drug_id",
                condition=Q(facility__isnull=False),
            ),

            # 2. Global uniqueness
            models.UniqueConstraint(
                fields=["eaushadhi_drug_id", "product_knowledge"],
                name="uniq_global_drug_id",
                condition=Q(facility__isnull=True),
            ),
        ]