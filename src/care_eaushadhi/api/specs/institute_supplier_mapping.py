import datetime
from pydantic import UUID4
from care.emr.resources.base import EMRResource
from care_eaushadhi.models.eaushadhi_institute_supplier_mapping import EAushadhiInstituteSupplierMapping

class InstituteSupplierMappingReadSpec(EMRResource):
    __model__ = EAushadhiInstituteSupplierMapping
    __exclude__ = []
    id: UUID4 | None = None
    supplier_id: UUID4 | None = None
    supplier_name: str | None = None
    eaushadhi_warehouse_name: str | None = None
    is_default: bool = False
    created_by: dict | None = None
    updated_by: dict | None = None
    created_date: datetime.datetime | None = None
    modified_date: datetime.datetime | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = obj.external_id
        mapping["supplier_id"] = obj.supplier.external_id if obj.supplier else None
        mapping["supplier_name"] = obj.supplier.name if obj.supplier else None
        cls.serialize_audit_users(mapping, obj)