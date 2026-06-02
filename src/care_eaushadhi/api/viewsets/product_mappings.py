from django.utils import timezone

from django.db import IntegrityError

from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as RestFrameworkValidationError

from care.emr.api.viewsets.base import (
    EMRCreateMixin,
    EMRListMixin,
    EMRUpdateMixin,
    EMRBaseViewSet,
)

from care_eaushadhi.models.eaushadhi_product_mapping import (
    EAushadhiProductMapping,
)
from care_eaushadhi.api.specs.product_mappings import (
    ProductMappingCreateSpec,
    ProductMappingReadSpec,
    ProductMappingUpdateSpec
    )


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

