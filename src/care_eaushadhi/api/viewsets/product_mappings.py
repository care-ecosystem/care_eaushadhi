from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRBaseViewSet,
)

from care_eaushadhi.models.eaushadhi_product_mapping import (
    EauShadhiProductMapping,
)
from care_eaushadhi.api.specs.product_mappings import (
    ProductMappingCreateSpec,
    ProductMappingReadSpec
    )


class ProductMappingViewSet(
    EMRCreateMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = EauShadhiProductMapping

    pydantic_model = ProductMappingCreateSpec
    pydantic_read_model = ProductMappingReadSpec
    pydantic_retrieve_model = None

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related(
                "facility",
                "product_knowledge",
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

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {
                    "errors": [
                        {
                            "type": "conflict",
                            "msg": "Product mapping already exists for this eAushadi drug and product knowledge combination",
                        }
                    ]
                },
                status=status.HTTP_409_CONFLICT,
            )

