from django.db import models

from care.emr.models.base import EMRBaseModel
from care.emr.models.organization import Organization

from care_eaushadhi.models.eaushadhi_institute_mapping import EAushadhiInstituteMapping

class EAushadhiInstituteSupplierMapping(EMRBaseModel):
    institute_mapping = models.ForeignKey(
        EAushadhiInstituteMapping,
        on_delete=models.CASCADE,
        related_name="supplier_mappings"
    )
    supplier = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        limit_choices_to={"org_type": "product_supplier"},
        related_name="eaushadhi_supplies"
    )
    eaushadhi_warehouse_name = models.CharField(max_length=255)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "E-Aushadhi Institute Supplier Mappings"
        indexes = [
            models.Index(
                fields=["institute_mapping", "deleted"],
                name="idx_institute_mapping_deleted"
            )
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["institute_mapping"],
                condition=models.Q(is_default=True, deleted=False),
                name="unique_default_supplier_per_institute"
            )
        ]

    def __str__(self):
        return f"{self.institute_mapping} - {self.eaushadhi_warehouse_name}"
