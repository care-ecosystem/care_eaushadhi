import datetime
from pydantic import UUID4

from care.emr.resources.base import EMRResource

from care_eaushadhi.models.eaushadhi_institute_mapping import EAushadhiInstituteMapping
from care_eaushadhi.api.specs.institute_supplier_mapping import InstituteSupplierMappingReadSpec


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