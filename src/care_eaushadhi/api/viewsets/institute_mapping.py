from django.db import transaction
from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.facility.models import Facility
from care.emr.models.organization import Organization
from care.utils.shortcuts import get_object_or_404

from care_eaushadhi.api.specs.institute_mapping import (
    InstituteMappingCreateSpec,
    InstituteMappingListSpec,
    InstituteMappingRetrieveSpec,
    InstituteMappingUpdateSpec,
)
from care_eaushadhi.models.eaushadhi_institute_mapping import EAushadhiInstituteMapping
from care_eaushadhi.models.eaushadhi_institute_supplier_mapping import EAushadhiInstituteSupplierMapping


class InstituteMappingFilters(filters.FilterSet):
    facility_id = filters.UUIDFilter(field_name="facility__external_id")
    eaushadhi_institute_id = filters.CharFilter(lookup_expr="iexact")
    schema_version = filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = EAushadhiInstituteMapping
        fields = ["facility_id", "eaushadhi_institute_id", "schema_version"]


class InstituteMappingViewSet(
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRBaseViewSet,
):
    database_model = EAushadhiInstituteMapping
    pydantic_model = InstituteMappingCreateSpec
    pydantic_read_model = InstituteMappingListSpec
    pydantic_retrieve_model = InstituteMappingRetrieveSpec
    pydantic_update_model = InstituteMappingUpdateSpec
    filterset_class = InstituteMappingFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

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

    def create(self, request, *args, **kwargs):
        """
        Create an institute mapping with optional supplier mappings.

        Validates:
        - Facility exists and doesn't already have a mapping
        - All supplier IDs exist
        - At most one supplier is marked as default
        """
        # Parse and validate input
        spec = InstituteMappingCreateSpec(**request.data)

        # Check if facility already has a mapping
        facility = get_object_or_404(Facility, external_id=spec.facility_id)
        if EAushadhiInstituteMapping.objects.filter(facility=facility, deleted=False).exists():
            return Response(
                {"error": "Institute mapping already exists for this facility"},
                status=status.HTTP_409_CONFLICT
            )

        # Validate all suppliers exist
        supplier_ids = [sm.supplier_id for sm in (spec.supplier_mappings or [])]
        if supplier_ids:
            suppliers = Organization.objects.filter(
                external_id__in=supplier_ids,
                org_type="product_supplier",
                deleted=False
            )
            if suppliers.count() != len(supplier_ids):
                found_ids = {s.external_id for s in suppliers}
                missing_ids = set(supplier_ids) - found_ids
                return Response(
                    {"error": f"Supplier(s) not found: {missing_ids}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Create institute mapping and supplier mappings atomically
        with transaction.atomic():
            # Create the institute mapping
            institute_mapping = EAushadhiInstituteMapping.objects.create(
                facility=facility,
                eaushadhi_institute_id=spec.eaushadhi_institute_id,
                schema_version=spec.schema_version,
                credentials_ref=spec.credentials_ref or "",
                meta=spec.meta or {},
                created_by=request.user,
                updated_by=request.user,
            )

            # Create supplier mappings if provided
            if spec.supplier_mappings:
                for sm_spec in spec.supplier_mappings:
                    supplier = Organization.objects.get(
                        external_id=sm_spec.supplier_id,
                        org_type="product_supplier"
                    )
                    EAushadhiInstituteSupplierMapping.objects.create(
                        institute_mapping=institute_mapping,
                        supplier=supplier,
                        eaushadhi_warehouse_name=sm_spec.eaushadhi_warehouse_name,
                        is_default=sm_spec.is_default,
                        created_by=request.user,
                        updated_by=request.user,
                    )

        # Fetch the created object with all relations
        institute_mapping = (
            EAushadhiInstituteMapping.objects
            .select_related("facility", "created_by", "updated_by")
            .prefetch_related(
                "supplier_mappings",
                "supplier_mappings__supplier",
                "supplier_mappings__created_by",
                "supplier_mappings__updated_by",
            )
            .get(pk=institute_mapping.pk)
        )

        # Serialize and return
        result = InstituteMappingRetrieveSpec.serialize(institute_mapping)
        return Response(
            result.to_json(),
            status=status.HTTP_201_CREATED
        )

    def partial_update(self, request, *args, **kwargs):
        """
        Update core institute mapping fields (PATCH).

        Only updates schema_version, credentials_ref, and meta.
        Does NOT modify supplier_mappings (use dedicated endpoint for that).
        All fields are optional - only supplied fields are updated.
        """
        # Get the existing institute mapping
        instance = self.get_object()

        # Parse and validate input (all fields optional for PATCH)
        spec = InstituteMappingUpdateSpec(**request.data)

        # Update only the fields that were provided
        updated = False
        if spec.schema_version is not None:
            instance.schema_version = spec.schema_version
            updated = True

        if spec.credentials_ref is not None:
            instance.credentials_ref = spec.credentials_ref
            updated = True

        if spec.meta is not None:
            instance.meta = spec.meta
            updated = True

        # Update modified metadata
        if updated:
            instance.updated_by = request.user
            instance.save()

        # Fetch the updated object with all relations
        instance = (
            EAushadhiInstituteMapping.objects
            .select_related("facility", "created_by", "updated_by")
            .prefetch_related(
                "supplier_mappings",
                "supplier_mappings__supplier",
                "supplier_mappings__created_by",
                "supplier_mappings__updated_by",
            )
            .get(pk=instance.pk)
        )

        # Serialize and return
        result = InstituteMappingRetrieveSpec.serialize(instance)
        return Response(
            result.to_json(),
            status=status.HTTP_200_OK
        )
