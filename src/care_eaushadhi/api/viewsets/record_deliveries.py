from django.db import IntegrityError
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    PermissionDenied,
    ValidationError,
)

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
)
from care.facility.models import Facility
from care.security.authorization.base import AuthorizationController

from care_eaushadhi.api.specs.record_delivery import (
    RecordDeliveryCreateSpec,
    RecordDeliveryReadSpec,
)
from care_eaushadhi.models.eaushadhi_inward_record_delivery import (
    EAushadhiInwardRecordDelivery,
)


class ConflictException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflict"
    default_code = "conflict"


class RecordDeliveryViewSet(
    EMRCreateMixin,
    EMRBaseViewSet,
):
    database_model = EAushadhiInwardRecordDelivery

    pydantic_model = RecordDeliveryCreateSpec
    pydantic_retrieve_model = RecordDeliveryReadSpec

    def authorize_create(self, instance):

        try:
            facility = Facility.objects.get(
                external_id=instance.facility_id
            )
        except Facility.DoesNotExist:
            raise ValidationError("Facility not found")

        if not AuthorizationController.call(
            "can_use_eaushadhi_integration",
            self.request.user,
            facility,
        ):
            raise PermissionDenied(
                "You are not authorized to use eAushadhi plugin for this facility"
            )

    def perform_create(self, instance):
        """
        instance is EAushadhiInwardRecordDelivery.
        """

        instance.created_by = self.request.user
        instance.updated_by = self.request.user

        try:
            instance.save()

        except IntegrityError as exc:
            constraint_name = getattr(
                getattr(exc.__cause__, "diag", None),
                "constraint_name",
                None,
            )

            if constraint_name == "care_eaushadhi_eaushadhiinwardrecorddeliv_delivery_order_id_key":
                raise ConflictException(
                    "delivery_order_id is already linked to an inward_record"
                ) from exc

            raise