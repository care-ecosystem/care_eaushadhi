import datetime
from pydantic import UUID4

from care.emr.resources.base import EMRResource

from care_eaushadhi.models.eaushadhi_institute_mapping import EAushadhiInstituteMapping
from care_eaushadhi.api.specs.institute_supplier_mapping import InstituteSupplierMappingReadSpec


class InstituteMappingListSpec(EMRResource):
    __model__ = EAushadhiInstituteMapping
    __exclude__ = []
    __store_metadata__ = True

    id: UUID4 | None = None
    facility_id: UUID4 | None = None
    eaushadhi_institute_id: str | None = None
    schema_version: str | None = None
    credentials_ref: str | None = None
    meta: dict | None = None
    supplier_mappings: list[dict] = []
    disable_inward_date: bool = False      
    manual_addition: bool = False          
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


class InstituteMappingWriteSpec(EMRResource):
    __model__ = EAushadhiInstituteMapping
    __store_metadata__ = True

    disable_inward_date: bool | None = None
    manual_addition: bool | None = None

    def de_serialize(self, obj=None, partial=False):
        if not obj:
            obj = self.__model__()
        meta = getattr(obj, "meta", {}) or {}
        if self.disable_inward_date is not None:
            meta["disable_inward_date"] = self.disable_inward_date
        if self.manual_addition is not None:
            meta["manual_addition"] = self.manual_addition
        obj.meta = meta
        obj.save()
        return obj
