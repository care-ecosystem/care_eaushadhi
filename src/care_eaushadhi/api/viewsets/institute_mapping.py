from uuid import UUID

from django.utils import timezone
from django.db import transaction, connection
from django_filters import rest_framework as filters

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from pydantic import ValidationError as PydanticValidationError

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.facility.models import Facility
from care.emr.models.organization import Organization
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404

from care_eaushadhi.api.specs.institute_mapping import (
    InstituteMappingCreateSpec,
    InstituteMappingListSpec,
    InstituteMappingRetrieveSpec,
    InstituteMappingUpdateSpec,
)
from care_eaushadhi.api.specs.institute_supplier_mapping import (
    InstituteSupplierMappingReadSpec,
    InstituteSupplierMappingCreateSpec,
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
    lookup_field = "external_id"

    def _authorize_facility(self, facility):
        if not AuthorizationController.call(
            "can_use_eaushadhi_integration", self.request.user, facility
        ):
            raise PermissionDenied(
                "You are not authorized to use eAushadhi plugin for this facility"
            )

    def authorize_retrieve(self, instance):
        self._authorize_facility(instance.facility)

    def get_queryset(self):
        queryset = (
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
        if self.action == "list":
            facility_id = self.request.query_params.get("facility_id")
            if facility_id:
                facility = get_object_or_404(Facility, external_id=facility_id)
                self._authorize_facility(facility)
                return queryset.filter(facility=facility)
        return queryset

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
        self._authorize_facility(facility)
        if EAushadhiInstituteMapping.objects.filter(facility=facility, deleted=False).exists():
            return Response(
                {"error": "Institute mapping already exists for this facility"},
                status=status.HTTP_409_CONFLICT
            )

        # Validate all suppliers exist
        supplier_ids = [sm.supplier_id for sm in (
            spec.supplier_mappings or [])]
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
        self._authorize_facility(instance.facility)

        # Parse and validate input (all fields optional for PATCH)
        spec = InstituteMappingUpdateSpec(**request.data)

        # Update only the fields that were provided
        updated = False

        if spec.eaushadhi_institute_id is not None:
            instance.eaushadhi_institute_id = spec.eaushadhi_institute_id
            updated = True

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

    @action(
        detail=True,
        methods=["patch"],
        url_path="supplier-mappings",
        url_name="supplier-mappings",
    )
    def replace_supplier_mappings(self, request, *args, **kwargs):
        institute_mapping = self.get_object()
        self._authorize_facility(institute_mapping.facility)

        supplier_mappings_data = request.data.get("supplier_mappings")
        if not isinstance(supplier_mappings_data, list) or not supplier_mappings_data:
            return Response(
                {"error": "supplier_mappings must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            supplier_mappings = [
                InstituteSupplierMappingCreateSpec(**item)
                for item in supplier_mappings_data
            ]
        except PydanticValidationError as exc:
            return Response(
                {"error": "Invalid supplier mapping data", "details": exc.errors()},
                status=status.HTTP_400_BAD_REQUEST,
            )

        supplier_ids = [sm.supplier_id for sm in supplier_mappings]

        if len(supplier_ids) != len(set(supplier_ids)):
            return Response(
                {"error": "Duplicate supplier_id values are not allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if sum(sm.is_default for sm in supplier_mappings) > 1:
            return Response(
                {"error": "Only one supplier can be marked as default."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        suppliers = Organization.objects.filter(
            external_id__in=supplier_ids,
            org_type="product_supplier",
            deleted=False,
        )

        if suppliers.count() != len(supplier_ids):
            found = {supplier.external_id for supplier in suppliers}
            missing = set(supplier_ids) - found
            return Response(
                {"error": f"Supplier(s) not found: {missing}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        suppliers_by_id = {
            supplier.external_id: supplier
            for supplier in suppliers
        }

        all_mappings = {
            mapping.supplier_id: mapping
            for mapping in EAushadhiInstituteSupplierMapping._base_manager.filter(
                institute_mapping=institute_mapping
            )
        }

        current_default = next(
            (
                mapping
                for mapping in all_mappings.values()
                if not mapping.deleted and mapping.is_default
            ),
            None,
        )

        incoming_default = next(
            (sm for sm in supplier_mappings if sm.is_default),
            None,
        )

        with transaction.atomic():

            for mapping in all_mappings.values():
                supplier_external_id = mapping.supplier.external_id

                if (
                    not mapping.deleted
                    and supplier_external_id not in supplier_ids
                ):
                    mapping.deleted = True
                    mapping.updated_by = request.user
                    mapping.save(update_fields=["deleted", "updated_by"])

            if (
                current_default
                and incoming_default
                and current_default.supplier.external_id != incoming_default.supplier_id
            ):
                current_default.is_default = False
                current_default.updated_by = request.user
                current_default.save(
                    update_fields=["is_default", "updated_by"])

            for spec in supplier_mappings:
                supplier = suppliers_by_id[spec.supplier_id]

                mapping = all_mappings.get(supplier.id)

                if mapping:
                    mapping.eaushadhi_warehouse_name = spec.eaushadhi_warehouse_name
                    mapping.is_default = spec.is_default
                    mapping.deleted = False
                    mapping.updated_by = request.user
                    mapping.save()
                else:
                    EAushadhiInstituteSupplierMapping.objects.create(
                        institute_mapping=institute_mapping,
                        supplier=supplier,
                        eaushadhi_warehouse_name=spec.eaushadhi_warehouse_name,
                        is_default=spec.is_default,
                        created_by=request.user,
                        updated_by=request.user,
                    )

        institute_mapping = (
            EAushadhiInstituteMapping.objects
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
            .get(pk=institute_mapping.pk)
        )

        result = InstituteMappingRetrieveSpec.serialize(institute_mapping)
        return Response(result.to_json(), status=status.HTTP_200_OK)
