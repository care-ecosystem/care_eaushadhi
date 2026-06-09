from django.db import IntegrityError
from django.utils import timezone
import logging

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as RestFrameworkValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRUpdateMixin,
)
from care.facility.models.facility import Facility
from care.security.authorization import AuthorizationController
from care.utils.shortcuts import get_object_or_404

from care_eaushadhi.api.specs.product_mappings import (
    ProductMappingCreateSpec,
    ProductMappingReadSpec,
    ProductMappingUpdateSpec,
)
from care_eaushadhi.fuzzy_matching import get_fuzzy_suggestions
from care_eaushadhi.models.eaushadhi_inward_record_item import EAushadhiInwardRecordItem
from care_eaushadhi.models.eaushadhi_product_mapping import EAushadhiProductMapping

logger = logging.getLogger(__name__)


class ProductMappingViewSet(
    EMRCreateMixin,
    EMRListMixin,
    EMRUpdateMixin,
    EMRBaseViewSet,
):
    http_method_names = ["get", "post", "patch"]

    database_model = EAushadhiProductMapping

    pydantic_model = ProductMappingCreateSpec
    pydantic_read_model = ProductMappingReadSpec
    pydantic_update_model = ProductMappingUpdateSpec
    pydantic_retrieve_model = None

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related(
                "facility",
                "product_knowledge",
                "product_knowledge__category",
                "product_knowledge__facility",
                "created_by",
                "updated_by",
            )
        )
        facility_id = self.request.query_params.get("facility_id")
        if facility_id:
            queryset = queryset.filter(facility__external_id=facility_id)

        # Filter by eaushadhi_drug_id
        eaushadhi_drug_id = self.request.query_params.get("eaushadhi_drug_id")
        if eaushadhi_drug_id:
            queryset = queryset.filter(eaushadhi_drug_id=eaushadhi_drug_id)

        # Ordering
        ordering = self.request.query_params.get("ordering", "-usage_count,-last_used_date")
        allowed_orderings = {
            "usage_count", "-usage_count",
            "last_used_date", "-last_used_date",
        }
        order_fields = [f.strip() for f in ordering.split(",")]
        valid_fields = [f for f in order_fields if f in allowed_orderings]
        if valid_fields:
            queryset = queryset.order_by(*valid_fields)

        return queryset
    def perform_update(self, instance):
        # Only write the two usage fields — avoids touching unrelated columns
        instance.updated_by = self.request.user
        instance.modified_date = timezone.now()
        instance.save(update_fields=["usage_count", "last_used_date", "updated_by_id", "modified_date"])

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        allowed_fields = {"usage_count", "last_used_date"}
        unexpected = set(request.data.keys()) - allowed_fields
        if unexpected:
            raise RestFrameworkValidationError(
                f"Only usage_count and last_used_date can be updated. Unexpected fields: {unexpected}"
            )
        return Response(self.handle_update(instance, request.data))

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            facility_id = request.data.get("facility_id")
            if facility_id:
                msg = (
                    "Product mapping already exists for facility, eAushadhi drug and product knowledge"
                )
            else:
                msg = (
                    "Global product mapping already exists for eAushadhi drug and product knowledge"
                )

            return Response(
                {
                    "errors": [
                        {
                            "type": "conflict",
                            "msg": msg,
                        }
                    ]
                },
                status=status.HTTP_409_CONFLICT,
            )



    @action(detail=False, methods=["get"])
    def search(self, request):
        facility_id = request.query_params.get("facility_id")
        eaushadhi_drug_id = request.query_params.get("eaushadhi_drug_id")

        if not eaushadhi_drug_id:
            return Response(
                {"errors": [{"type": "validation_error", "msg": "eaushadhi_drug_id is required"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not facility_id:
            return Response(
                {"errors": [{"type": "validation_error", "msg": "facility_id is required"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        facility = get_object_or_404(Facility, external_id=facility_id)

        existing_mappings = EAushadhiProductMapping.objects.filter(
            facility=facility,
            eaushadhi_drug_id=eaushadhi_drug_id,
        ).order_by("-usage_count").select_related(
            "product_knowledge",
            "product_knowledge__category",
            "product_knowledge__facility",
            "created_by",
            "updated_by",
        )

        results = []
        processed_product_knowledge_ids = set()

        for mapping in existing_mappings:
            data = ProductMappingReadSpec.serialize(mapping).to_json()
            results.append(data)
            processed_product_knowledge_ids.add(mapping.product_knowledge_id)

        inward_record_item = EAushadhiInwardRecordItem.objects.filter(
            drug_id=eaushadhi_drug_id,
        ).order_by("-receipt_date", "-created_date").first()

        if inward_record_item:
            drug_name = inward_record_item.drug_name
            logger.info(
                "fuzzy search | drug_id=%s drug_name=%s",
                eaushadhi_drug_id,
                drug_name,
            )
            suggestions = get_fuzzy_suggestions(drug_name, facility)
            for pk in suggestions:
                if pk.id in processed_product_knowledge_ids:
                    continue
                preview_mapping = EAushadhiProductMapping(
                    facility=facility,
                    eaushadhi_drug_id=eaushadhi_drug_id,
                    eaushadhi_drug_name=drug_name,
                    product_knowledge=pk,
                    usage_count=0,
                    last_used_date=None,
                    created_by=request.user,
                    updated_by=request.user,
                )
                data = ProductMappingReadSpec.serialize(preview_mapping).to_json()
                results.append(data)
                processed_product_knowledge_ids.add(pk.id)

        existing_count = existing_mappings.count()
        no_suggestions = len(results) == existing_count
        can_write_product_knowledge = AuthorizationController.call(
            "can_write_facility_product_knowledge", request.user, facility
        )
        can_create = no_suggestions and can_write_product_knowledge

        return Response({"results": results, "can_create": can_create})
