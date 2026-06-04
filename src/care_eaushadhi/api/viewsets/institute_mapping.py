from django_filters import rest_framework as filters
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin, 
)

from care_eaushadhi.api.specs.institute_mapping import (
    InstituteMappingListSpec,
    InstituteMappingRetrieveSpec,
    InstituteMappingWriteSpec,
)
from care_eaushadhi.models.eaushadhi_institute_mapping import EAushadhiInstituteMapping


class InstituteMappingFilters(filters.FilterSet):
    facility_id = filters.UUIDFilter(field_name="facility__external_id")
    eaushadhi_institute_id = filters.CharFilter(lookup_expr="iexact")
    schema_version = filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = EAushadhiInstituteMapping
        fields = ["facility_id", "eaushadhi_institute_id", "schema_version"]


class InstituteMappingViewSet(
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRBaseViewSet,
):
    database_model = EAushadhiInstituteMapping
    pydantic_read_model = InstituteMappingListSpec
    pydantic_write_model = InstituteMappingWriteSpec
    pydantic_retrieve_model = InstituteMappingRetrieveSpec
    filterset_class = InstituteMappingFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]
    def get_update_pydantic_model(self):  # ← add this
        return self.pydantic_write_model

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "facility",
                "created_by",
                "updated_by",
            )
            .prefetch_related(
                "supplier_mappings",
                "supplier_mappings__supplier",
                "supplier_mappings__created_by",
                "supplier_mappings__updated_by",
                
            )
        )
        