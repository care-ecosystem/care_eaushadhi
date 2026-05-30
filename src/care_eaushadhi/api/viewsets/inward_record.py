from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRListMixin,
    EMRRetrieveMixin,
)

from care_eaushadhi.api.specs.inward_record import (
    InwardRecordListSpec,
    InwardRecordRetrieveSpec
)
from care_eaushadhi.models.eaushadhi_inward_record import EAushadhiInwardRecord


class InwardRecordFilters(filters.FilterSet):
    facility_id = filters.UUIDFilter(field_name="facility__external_id")
    inward_date = filters.DateFilter(field_name="inward_date")
    sync_status = filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = EAushadhiInwardRecord
        fields = ["facility_id", "inward_date", "sync_status"]


class InwardRecordViewSet(
    EMRListMixin,
    EMRRetrieveMixin,
    EMRBaseViewSet,
):
    database_model = EAushadhiInwardRecord
    pydantic_read_model = InwardRecordListSpec
    pydantic_retrieve_model = InwardRecordRetrieveSpec
    filterset_class = InwardRecordFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["inward_date", "created_date", "modified_date"]

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related(
                "facility",
                "last_successful_fetch_log",
                "last_attempted_fetch_log",
                "created_by",
                "updated_by",
            )
        )
        # facility_id is required for list
        if self.action == "list":
            facility_id = self.request.GET.get("facility_id")
            if not facility_id:
                raise ValidationError(
                    {"facility_id": ["This field is required"]}
                )
            return queryset.filter(facility__external_id=facility_id)
        return queryset
