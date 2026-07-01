from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRListMixin,
    EMRRetrieveMixin,
)
from care.facility.models import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.pagination.care_pagination import CareLimitOffsetPagination
from care.utils.shortcuts import get_object_or_404

from care_eaushadhi.api.specs.inward_record import (
    InwardRecordListSpec,
    InwardRecordRetrieveSpec
)
from care_eaushadhi.api.specs.inward_record_item import InwardRecordItemReadSpec
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

    def _authorize_facility(self, facility):
        if not AuthorizationController.call(
            "can_use_eaushadhi_integration", self.request.user, facility
        ):
            raise PermissionDenied(
                "You are not authorized to use eAushadhi plugin for this facility"
            )

    def authorize_retrieve(self, instance):
        self._authorize_facility(instance.facility)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        self.authorize_retrieve(instance)

        items_queryset = instance.items.prefetch_related("item_deliveries").order_by(
            "pk"
        )
        warehouse_name = request.GET.get("warehouse_name")
        if warehouse_name:
            items_queryset = items_queryset.filter(warehouse_name__iexact=warehouse_name)

        paginator = CareLimitOffsetPagination()
        page = paginator.paginate_queryset(items_queryset, request)
        items_payload = {
            "count": paginator.count,
            "results": [
                InwardRecordItemReadSpec.serialize(item).to_json() for item in page
            ],
        }

        data = (
            self.get_retrieve_pydantic_model()
            .serialize(
                instance,
                request.user,
                items=items_payload,
                **self.get_serializer_retrieve_context(),
            )
            .to_json()
        )
        return Response(data)

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
            facility = get_object_or_404(Facility, external_id=facility_id)
            self._authorize_facility(facility)
            return queryset.filter(facility=facility)
        return queryset
