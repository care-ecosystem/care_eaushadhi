from django.db import IntegrityError
from django.utils import timezone
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
from care_eaushadhi.models.eaushadhi_product_mapping import (
    EAushadhiProductMapping,
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

    def perform_create(self, instance):

        self._authorize_facility(instance.facility)
        instance.created_by = self.request.user
        instance.updated_by = self.request.user

        try:
            instance.save()
            self._sync_product_mapping(instance)
        except IntegrityError as exc:
            raise

    def _sync_product_mapping(self, delivery_item):

        facility = delivery_item.facility
        eaushadhi_drug_id = delivery_item.inward_record_item.drug_id
        product_knowledge = delivery_item.product_knowledge
        eaushadhi_drug_name = delivery_item.inward_record_item.drug_name
 
        mapping, created = EAushadhiProductMapping.objects.get_or_create(
            facility=facility,
            eaushadhi_drug_id=eaushadhi_drug_id,
            product_knowledge=product_knowledge,
            defaults={
                'eaushadhi_drug_name': eaushadhi_drug_name,
                'usage_count': 1,
                'last_used_date': timezone.now(),
                'created_by': self.request.user,
                'updated_by': self.request.user,
            }
        )
 
        if not created:
            from django.db.models import F
            EAushadhiProductMapping.objects.filter(pk=mapping.pk).update(
                usage_count=F('usage_count') + 1,
                last_used_date=timezone.now(),
                updated_by=self.request.user,
            )

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
        return Response(self.handle_update(instance, request.data))
    
    def authorize_update(self, request_obj, model_instance):
        self._authorize_facility(model_instance.facility)

    def perform_update(self, instance):
        instance.updated_by = self.request.user
        instance.save()