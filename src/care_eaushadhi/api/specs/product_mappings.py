from pydantic import UUID4
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import ValidationError as RestFrameworkValidationError


from care.emr.resources.base import EMRResource
from care.facility.models import Facility
from care.emr.models import ProductKnowledge
from care.emr.resources.inventory.product_knowledge.spec import ProductKnowledgeReadSpec

from care_eaushadhi.models.eaushadhi_product_mapping import (
    EAushadhiProductMapping,
)



class ProductMappingCreateSpec(EMRResource):
    __model__ = EAushadhiProductMapping

    facility_id: UUID4 | None = None
    eaushadhi_drug_id: str
    eaushadhi_drug_name: str
    product_knowledge_id: UUID4

    def perform_extra_deserialization(self, is_update, obj):
        if self.facility_id:
            try:
                obj.facility = Facility.objects.get(external_id=self.facility_id)
            except ObjectDoesNotExist:
                raise RestFrameworkValidationError("Facility not found")
        else:
            obj.facility = None

        try:
            obj.product_knowledge = ProductKnowledge.objects.get(
                external_id=self.product_knowledge_id
            )
        except ObjectDoesNotExist:
            raise RestFrameworkValidationError("ProductKnowledge not found")

        return obj

class ProductMappingReadSpec(EMRResource):
    __model__ = EAushadhiProductMapping

    id: UUID4 | None = None
    facility_id: UUID4 | None = None
    eaushadhi_drug_id: str
    eaushadhi_drug_name: str
    product_knowledge: dict | None = None
    usage_count: int = 0
    last_used_date: str | None = None
    deleted: bool = False
    created_by: dict | None = None
    updated_by: dict | None = None
    created_date: str | None = None
    modified_date: str | None = None

    @classmethod
    def perform_extra_serialization(cls, mapping, obj):
        mapping["id"] = str(obj.external_id)
        mapping["facility_id"] = str(obj.facility.external_id) if obj.facility else None
        # mapping["product_knowledge_id"] = str(obj.product_knowledge.external_id)
        mapping["product_knowledge"] = ProductKnowledgeReadSpec.serialize(
            obj.product_knowledge
        ).to_json()
        mapping["usage_count"] = obj.usage_count
        mapping["last_used_date"] = obj.last_used_date.isoformat() if obj.last_used_date else None
        mapping["deleted"] = obj.deleted
        mapping["created_date"] = obj.created_date.isoformat() if obj.created_date else None
        mapping["modified_date"] = obj.modified_date.isoformat() if obj.modified_date else None

        if obj.created_by:
            mapping["created_by"] = {
                "id": str(obj.created_by.external_id),
                "username": obj.created_by.username,
                "first_name": obj.created_by.first_name,
                "last_name": obj.created_by.last_name,
                "email": obj.created_by.email,
            }
        if obj.updated_by:
            mapping["updated_by"] = {
                "id": str(obj.updated_by.external_id),
                "username": obj.updated_by.username,
                "first_name": obj.updated_by.first_name,
                "last_name": obj.updated_by.last_name,
                "email": obj.updated_by.email,
            }

class ProductMappingUpdateSpec(EMRResource):
    __model__ = EAushadhiProductMapping

    usage_count: int
    last_used_date: datetime

    def perform_extra_deserialization(self, is_update, obj):
        obj.usage_count = self.usage_count
        obj.last_used_date = self.last_used_date
        return obj
