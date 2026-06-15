from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from care.emr.models.supply_delivery import SupplyDelivery
from care.emr.models.product import Product
from care.emr.models.product_knowledge import ProductKnowledge
from care.facility.models import Facility

from care_eaushadhi.models.eaushadhi_inward_record_item import EAushadhiInwardRecordItem
from care_eaushadhi.models.eaushadhi_inward_record_delivery import EAushadhiInwardRecordDelivery
from care_eaushadhi.models.eaushadhi_inward_record_item_delivery import (
    EAushadhiInwardRecordItemDelivery,
    InwardRecordItemDeliveryStatus,
)


class RecordItemDeliveryViewSet(GenericViewSet):

    def _authorize_facility(self, facility):
        if not AuthorizationController.call(
            "can_use_eaushadhi_integration", self.request.user, facility
        ):
            raise PermissionDenied(
                "You are not authorized to use eAushadhi plugin for this facility"
            )

    def create(self, request, *args, **kwargs):
        record_item_id = request.data.get("record_item_id")
        facility_id = request.data.get("facility_id")
        supply_delivery_id = request.data.get("supply_delivery_id")
        record_delivery_id = request.data.get("record_delivery_id")
        product_id = request.data.get("product_id")
        product_knowledge_id = request.data.get("product_knowledge_id")
        quantity_received = request.data.get("quantity_received")

        # Required field validation
        required_fields = {
            "record_item_id": record_item_id,
            "facility_id": facility_id,
            "supply_delivery_id": supply_delivery_id,
            "record_delivery_id": record_delivery_id,
            "product_id": product_id,
            "product_knowledge_id": product_knowledge_id,
            "quantity_received": quantity_received,
        }
        missing = {k: ["This field is required"] for k, v in required_fields.items() if not v}
        if missing:
            raise ValidationError(missing)

        # Resolve FKs
        record_item = get_object_or_404(
            EAushadhiInwardRecordItem, external_id=record_item_id
        )
        facility = get_object_or_404(Facility, external_id=facility_id)
        self._authorize_facility(facility)
        inward_record_delivery = get_object_or_404(
            EAushadhiInwardRecordDelivery, external_id=record_delivery_id
        )
        product = get_object_or_404(Product, external_id=product_id)
        product_knowledge = get_object_or_404(
            ProductKnowledge, external_id=product_knowledge_id
        )

        supply_delivery = None
        if supply_delivery_id:
            supply_delivery = get_object_or_404(
                SupplyDelivery, external_id=supply_delivery_id
            )

        try:
            delivery = EAushadhiInwardRecordItemDelivery.objects.create(
                inward_record_item=record_item,
                facility=facility,
                supply_delivery=supply_delivery,
                inward_record_delivery=inward_record_delivery,
                product=product,
                product_knowledge=product_knowledge,
                quantity_received=quantity_received,
                created_by=request.user,
                updated_by=request.user,
            )
        except IntegrityError:
            return Response(
                {
                    "errors": [
                        {
                            "type": "conflict",
                            "msg": "An active delivery already exists for this record_item",
                        }
                    ]
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "id": str(delivery.external_id),
                "inward_record_id": str(delivery.inward_record_delivery.inward_record.external_id),
                "delivery_order_id": str(delivery.inward_record_delivery.delivery_order.external_id),
                "facility_id": str(delivery.facility.external_id),
                "created_by": {
                    "id": str(request.user.external_id),
                    "username": request.user.username,
                    "first_name": request.user.first_name,
                    "last_name": request.user.last_name,
                    "email": request.user.email,
                },
                "updated_by": {
                    "id": str(request.user.external_id),
                    "username": request.user.username,
                    "first_name": request.user.first_name,
                    "last_name": request.user.last_name,
                    "email": request.user.email,
                },
                "created_date": str(delivery.created_date),
                "modified_date": str(delivery.modified_date),
            },
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        external_id = kwargs.get("pk")
        delivery = get_object_or_404(EAushadhiInwardRecordItemDelivery, external_id=external_id)
        self._authorize_facility(delivery.facility)

        quantity_received = request.data.get("quantity_received")
        new_status = request.data.get("status")

        errors = {}
        if new_status is not None and new_status not in InwardRecordItemDeliveryStatus.values:
            errors["status"] = [
                f"Must be one of: {', '.join(InwardRecordItemDeliveryStatus.values)}"
            ]
        if errors:
            raise ValidationError(errors)

        updated = False
        if quantity_received is not None:
            delivery.quantity_received = quantity_received
            updated = True
        if new_status is not None:
            delivery.status = new_status
            updated = True

        if updated:
            delivery.updated_by = request.user
            delivery.save()

        return Response(
            {
                "id": str(delivery.external_id),
                "quantity_received": str(delivery.quantity_received),
                "status": delivery.status,
                "inward_record_id": str(delivery.inward_record_delivery.inward_record.external_id),
                "delivery_order_id": str(delivery.inward_record_delivery.delivery_order.external_id),
                "facility_id": str(delivery.facility.external_id),
                "updated_by": {
                    "id": str(delivery.updated_by.external_id),
                    "username": delivery.updated_by.username,
                    "first_name": delivery.updated_by.first_name,
                    "last_name": delivery.updated_by.last_name,
                    "email": delivery.updated_by.email,
                },
                "created_date": str(delivery.created_date),
                "modified_date": str(delivery.modified_date),
            },
            status=status.HTTP_200_OK,
        )
