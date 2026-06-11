import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from care.emr.resources.base import EMRResource
from care_eaushadhi.models.eaushadhi_institute_supplier_mapping import EAushadhiInstituteSupplierMapping


class InstituteSupplierMappingReadSpec(EMRResource):
    """Read spec for supplier mappings (GET, returned in responses)."""
    __model__ = EAushadhiInstituteSupplierMapping
    __exclude__ = []

    id: UUID | None = None
    supplier_id: UUID | None = None
    supplier_name: str | None = None
    eaushadhi_warehouse_name: str | None = None
    is_default: bool = False
    created_by: dict | None = None
    updated_by: dict | None = None
    created_date: datetime.datetime | None = None
    modified_date: datetime.datetime | None = None

    def to_json(self):
        return self.model_dump(mode="json")

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        """Serialize external_id as id and supplier details."""
        mapping["id"] = obj.external_id
        mapping["supplier_id"] = obj.supplier.external_id if obj.supplier else None
        mapping["supplier_name"] = obj.supplier.name if obj.supplier else None
        cls.serialize_audit_users(mapping, obj)


class InstituteSupplierMappingCreateSpec(EMRResource):

    __model__ = EAushadhiInstituteSupplierMapping
    __exclude__ = ["id", "created_by", "updated_by", "created_date", "modified_date", "deleted", "external_id", "history", "institute_mapping"]

    id: Optional[UUID] = Field(
        None,
        description="Record external_id if updating existing record. Omit to create new."
    )
    supplier_id: UUID = Field(
        ...,
        description="Supplier UUID (from Organization.external_id)"
    )
    eaushadhi_warehouse_name: str = Field(
        ...,
        min_length=1,
        description="Warehouse name"
    )
    is_default: bool = Field(
        False,
        description="Mark as default supplier"
    )

    @field_validator("eaushadhi_warehouse_name")
    @classmethod
    def warehouse_name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Warehouse name cannot be empty")
        return v.strip()


class InstituteSupplierMappingUpdateSpec(EMRResource):
    __model__ = EAushadhiInstituteSupplierMapping
    __exclude__ = ["id", "created_by", "updated_by", "created_date", "modified_date", "deleted", "external_id", "history", "institute_mapping"]

    supplier_id: UUID
    eaushadhi_warehouse_name: str
    is_default: bool = False

    @field_validator("eaushadhi_warehouse_name")
    @classmethod
    def warehouse_name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Warehouse name cannot be empty")
        return v.strip()