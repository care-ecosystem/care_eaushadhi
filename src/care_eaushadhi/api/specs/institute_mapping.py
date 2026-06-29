import datetime
from pydantic import UUID4, field_validator

from care.emr.resources.base import EMRResource

from care_eaushadhi.models.eaushadhi_institute_mapping import EAushadhiInstituteMapping
from care_eaushadhi.api.specs.institute_supplier_mapping import InstituteSupplierMappingReadSpec, InstituteSupplierMappingCreateSpec


class InstituteMappingListSpec(EMRResource):
    __model__ = EAushadhiInstituteMapping
    __exclude__ = []

    id: UUID4 | None = None
    facility_id: UUID4 | None = None
    eaushadhi_institute_id: str | None = None
    schema_version: str | None = None
    credentials_ref: str | None = None
    meta: dict | None = None
    supplier_mappings: list[dict] = []
    created_by: dict | None = None
    updated_by: dict | None = None
    created_date: datetime.datetime | None = None
    modified_date: datetime.datetime | None = None

    def to_json(self):
        return self.model_dump(mode="json")  # no exclude, so meta will show

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["facility_id"] = obj.facility.external_id if obj.facility else None
        mapping["meta"] = dict(obj.meta) if obj.meta else {}
        mapping["supplier_mappings"] = [
            InstituteSupplierMappingReadSpec.serialize(sm).to_json()
            for sm in obj.supplier_mappings.all()
        ]
        cls.serialize_audit_users(mapping, obj)

class InstituteMappingRetrieveSpec(InstituteMappingListSpec):
    pass


class InstituteMappingCreateSpec(EMRResource):
    """Input spec for creating an institute mapping with optional supplier mappings."""
    __model__ = EAushadhiInstituteMapping
    __exclude__ = ["id", "created_by", "updated_by", "created_date", "modified_date", "deleted", "external_id", "history"]

    facility_id: UUID4
    eaushadhi_institute_id: str
    schema_version: str
    credentials_ref: str | None = None
    meta: dict | None = None
    supplier_mappings: list[InstituteSupplierMappingCreateSpec] | None = []

    @field_validator("supplier_mappings")
    @classmethod
    def validate_supplier_mappings(cls, v):
        """Validate that at most one supplier mapping is marked as default."""
        if v:
            default_count = sum(1 for sm in v if sm.is_default)
            if default_count > 1:
                raise ValueError("At most one supplier_mapping may be marked is_default = true")
        return v


class InstituteMappingUpdateSpec(EMRResource):
    """
    Input spec for updating core institute mapping fields.

    All fields are optional - only supplied fields are updated.
    Does NOT modify supplier_mappings (use dedicated endpoint for that).
    """
    __model__ = EAushadhiInstituteMapping
    __exclude__ = ["id", "facility", "created_by", "updated_by", "created_date", "modified_date", "deleted", "external_id", "history"]

    eaushadhi_institute_id: str | None = None
    schema_version: str | None = None
    credentials_ref: str | None = None
    meta: dict | None = None
