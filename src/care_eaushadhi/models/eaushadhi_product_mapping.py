from django.db import models
from django.db.models import Q
from care.emr.models.base import EMRBaseModel
from care.facility.models import Facility
from care.emr.models import ProductKnowledge

class ProductMappingType(models.TextChoices):
    BULK_IMPORT = "BULK_IMPORT"
    MANUAL = "MANUAL"

class EAushadhiProductMapping(EMRBaseModel):
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="eaushadhi_product_mappings",
        help_text="Facility-specific or global if null"
    )

    eaushadhi_drug_id = models.CharField(max_length=255, db_index=True)
    eaushadhi_drug_name = models.CharField(max_length=500)

    product_knowledge = models.ForeignKey(
        ProductKnowledge,
        on_delete=models.PROTECT,
        related_name="eaushadhi_mappings"
    )

    mapping_type = models.CharField(
        choices=ProductMappingType.choices,
        default=ProductMappingType.MANUAL,
        max_length=20
    )

    usage_count = models.IntegerField(default=0)
    last_used_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "E-Aushadhi Product Mappings"
        constraints = [
            # Facility-specific: same (facility, drug, product_knowledge, mapping_type) must be unique
            models.UniqueConstraint(
                fields=["facility", "eaushadhi_drug_id", "product_knowledge", "mapping_type"],
                name="uniq_facility_drug_pk_type",
                condition=Q(facility__isnull=False),
            ),
            # Global: same (drug, product_knowledge, mapping_type) must be unique
            models.UniqueConstraint(
                fields=["eaushadhi_drug_id", "product_knowledge", "mapping_type"],
                name="uniq_global_drug_pk_type",
                condition=Q(facility__isnull=True),
            ),
            # At most one BULK_IMPORT per (facility, drug)
            models.UniqueConstraint(
                fields=["facility", "eaushadhi_drug_id"],
                name="uniq_facility_drug_bulk_import",
                condition=Q(facility__isnull=False, mapping_type=ProductMappingType.BULK_IMPORT),
            ),
            # At most one global BULK_IMPORT per drug
            models.UniqueConstraint(
                fields=["eaushadhi_drug_id"],
                name="uniq_global_drug_bulk_import",
                condition=Q(facility__isnull=True, mapping_type=ProductMappingType.BULK_IMPORT),
            ),
        ]
