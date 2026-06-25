from django.db import IntegrityError
from django.utils import timezone
import logging

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError as RestFrameworkValidationError
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
from care_eaushadhi.models.eaushadhi_inward_record import EAushadhiInwardRecord
from care_eaushadhi.models.eaushadhi_inward_record_item import EAushadhiInwardRecordItem
from care_eaushadhi.models.eaushadhi_product_mapping import EAushadhiProductMapping, ProductMappingType

logger = logging.getLogger(__name__)


class ProductMappingViewSet(
    EMRCreateMixin,
    EMRListMixin,
    EMRUpdateMixin,
    EMRBaseViewSet,
):
    http_method_names = ["get", "post", "patch"]

    def _authorize_facility(self, facility):
        if not AuthorizationController.call(
            "can_use_eaushadhi_integration", self.request.user, facility
        ):
            raise PermissionDenied(
                "You are not authorized to use eAushadhi plugin for this facility"
            )

    database_model = EAushadhiProductMapping

    pydantic_model = ProductMappingCreateSpec
    pydantic_read_model = ProductMappingReadSpec
    pydantic_update_model = ProductMappingUpdateSpec
    pydantic_retrieve_model = None

    def authorize_create(self, instance):
        if instance.facility_id:
            facility = get_object_or_404(Facility, external_id=instance.facility_id)
            self._authorize_facility(facility)
        elif not self.request.user.is_superuser:
            raise PermissionDenied(
                "Only superusers can create global product mappings"
            )

    def authorize_update(self, request_obj, model_instance):
        if model_instance.facility:
            self._authorize_facility(model_instance.facility)
        elif not self.request.user.is_superuser:
            raise PermissionDenied(
                "Only superusers can update global product mappings"
            )

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
            facility = get_object_or_404(Facility, external_id=facility_id)
            self._authorize_facility(facility)
            queryset = queryset.filter(facility=facility)
        elif not self.request.user.is_superuser:
            raise PermissionDenied(
                "Only superusers can list global product mappings"
            )

        # Filter by eaushadhi_drug_id
        eaushadhi_drug_id = self.request.query_params.get("eaushadhi_drug_id")
        if eaushadhi_drug_id:
            queryset = queryset.filter(eaushadhi_drug_id=eaushadhi_drug_id)

        # Filter by mapping_type
        mapping_type = self.request.query_params.get("mapping_type")
        if mapping_type:
            queryset = queryset.filter(mapping_type=mapping_type)

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
            mapping_type = request.data.get("mapping_type", "MANUAL")
            if facility_id:
                if mapping_type == "BULK_IMPORT":
                    msg = "A BULK_IMPORT mapping already exists for this facility and eAushadhi drug"
                else:
                    msg = "Product mapping already exists for facility, eAushadhi drug, product knowledge and mapping type"
            else:
                if mapping_type == "BULK_IMPORT":
                    msg = "A global BULK_IMPORT mapping already exists for this eAushadhi drug"
                else:
                    msg = "Global product mapping already exists for eAushadhi drug, product knowledge and mapping type"

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
        self._authorize_facility(facility)

        existing_mappings = EAushadhiProductMapping.objects.filter(
            facility=facility,
            eaushadhi_drug_id=eaushadhi_drug_id,
        ).order_by("-usage_count", "-last_used_date").select_related(
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
                    mapping_type="MANUAL",
                    usage_count=0,
                    last_used_date=None,
                    created_by=request.user,
                    updated_by=request.user,
                )
                data = ProductMappingReadSpec.serialize(preview_mapping).to_json()
                results.append(data)
                processed_product_knowledge_ids.add(pk.id)

        can_write_product_knowledge = AuthorizationController.call(
            "can_write_facility_product_knowledge", request.user, facility
        )

        return Response({"results": results, "can_create": can_write_product_knowledge})

    @action(detail=False, methods=["get"], url_path="default-mapping")
    def default_mapping(self, request):
        inward_record_id = request.query_params.get("inward_record_id")
        if not inward_record_id:
            return Response(
                {"errors": [{"type": "validation_error", "msg": "inward_record_id is required"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inward_record = get_object_or_404(EAushadhiInwardRecord, external_id=inward_record_id)
        self._authorize_facility(inward_record.facility)

        drug_ids = list(
            EAushadhiInwardRecordItem.objects.filter(inward_record=inward_record)
            .values_list("drug_id", flat=True)
            .distinct()
        )

        mappings = EAushadhiProductMapping.objects.filter(
            facility=inward_record.facility,
            eaushadhi_drug_id__in=drug_ids,
            mapping_type=ProductMappingType.BULK_IMPORT,
        ).select_related(
            "product_knowledge",
            "product_knowledge__category",
            "product_knowledge__facility",
            "created_by",
            "updated_by",
        )

        results = []
        for mapping in mappings:
            results.append(ProductMappingReadSpec.serialize(mapping).to_json())

        return Response({"results": results})
