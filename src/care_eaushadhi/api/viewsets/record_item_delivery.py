from django.db import IntegrityError

from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import (
    APIException,
    PermissionDenied,
    ValidationError,
)

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRUpdateMixin,
)
from care.facility.models import Facility
from care.security.authorization.base import AuthorizationController

from care_eaushadhi.api.specs.record_item_delivery import (
    RecordItemDeliveryCreateSpec,
    RecordItemDeliveryReadSpec,
    RecordItemDeliveryUpdateSpec,
)
from care_eaushadhi.models.eaushadhi_inward_record_item_delivery import (
    EAushadhiInwardRecordItemDelivery,
    InwardRecordItemDeliveryStatus,
)


class ConflictException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "An active delivery already exists for this record_item"
    default_code = "conflict"


class RecordItemDeliveryViewSet(
    EMRCreateMixin,
    EMRUpdateMixin,
    EMRBaseViewSet,
):

    http_method_names = ["post", "patch"]

    database_model = EAushadhiInwardRecordItemDelivery

    pydantic_model = RecordItemDeliveryCreateSpec
    pydantic_retrieve_model = RecordItemDeliveryReadSpec
    pydantic_update_model = RecordItemDeliveryUpdateSpec

    def _authorize_facility(self, facility):
        if not AuthorizationController.call(
            "can_use_eaushadhi_integration",
            self.request.user,
            facility,
        ):
            raise PermissionDenied(
                "You are not authorized to use eAushadhi plugin for this facility"
            )

    def _check_duplicate_record(self, instance):

        try:
            # Simply check if another active delivery exists for this record_item
            existing = EAushadhiInwardRecordItemDelivery.objects.filter(
                inward_record_item=instance.inward_record_item,
                deleted=False
            ).exclude(pk=instance.pk)

            if existing.exists():
                return True

            return False
        except (AttributeError, TypeError) as e:
            return False

    def authorize_create(self, instance):
        self._authorize_facility(instance.facility)

    def perform_create(self, instance):
        instance.created_by = self.request.user
        instance.updated_by = self.request.user

        if self._check_duplicate_record(instance):
            raise ConflictException(
                "An active delivery already exists for this record_item"
            )

        try:
            instance.save()
        except IntegrityError as exc:
            constraint_name = getattr(
                getattr(exc.__cause__, "diag", None),
                "constraint_name",
                None,
            )

            if constraint_name and "inward_record_item" in constraint_name:
                raise ConflictException(
                    "An active delivery already exists for this record_item"
                ) from exc

            raise ConflictException() from exc

    def clean_update_data(self, request_data, keep_fields: set | None = None):
        clean_data = super().clean_update_data(request_data, keep_fields)

        allowed_fields = {"quantity_received", "status"}
        unexpected = set(clean_data.keys()) - allowed_fields

        if unexpected:
            raise ValidationError(
                f"Only quantity_received and status can be updated. "
                f"Unexpected fields: {', '.join(unexpected)}"
            )

        return clean_data

    def validate_data(self, instance, model_obj=None):

        if hasattr(instance, "status") and instance.status is not None:
            valid_statuses = [s[0]
                              for s in InwardRecordItemDeliveryStatus.choices]
            if instance.status not in valid_statuses:
                raise ValidationError(
                    {
                        "status": [
                            f"Must be one of: {', '.join(valid_statuses)}"
                        ]
                    }
                )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()

        allowed_fields = {"quantity_received", "status"}
        unexpected = set(request.data.keys()) - allowed_fields

        if unexpected:
            raise ValidationError(
                f"Only quantity_received and status can be updated. "
                f"Unexpected fields: {', '.join(unexpected)}"
            )

        return Response(self.handle_update(instance, request.data))

    def authorize_update(self, request_obj, model_instance):
        self._authorize_facility(model_instance.facility)

    def perform_update(self, instance):
        instance.updated_by = self.request.user
        instance.save()
