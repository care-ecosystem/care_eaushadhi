from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.utils.shortcuts import get_object_or_404
from care.facility.models import Facility
from care.emr.models.supply_delivery import DeliveryOrder

from care_eaushadhi.models.eaushadhi_inward_record import EAushadhiInwardRecord
from care_eaushadhi.models.eaushadhi_inward_record_delivery import (
    EAushadhiInwardRecordDelivery,
)
from care.emr.resources.user.spec import UserSpec


class RecordDeliveryViewSet(GenericViewSet):

    def create(self, request, *args, **kwargs):
        inward_record_id = request.data.get("inward_record_id")
        facility_id = request.data.get("facility_id")
        delivery_order_id = request.data.get("delivery_order_id")

        # --- 400: required field validation ---
        required_fields = {
            "inward_record_id": inward_record_id,
            "facility_id": facility_id,
            "delivery_order_id": delivery_order_id,
        }
        details = {
            field: ["This field is required"]
            for field, value in required_fields.items()
            if not value
        }
        if details:
            return Response(
                {"error": "Invalid input parameters", "details": details},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- resolve FKs (404 if any external_id is unknown) ---
        inward_record = get_object_or_404(
            EAushadhiInwardRecord, external_id=inward_record_id
        )
        facility = get_object_or_404(Facility, external_id=facility_id)
        delivery_order = get_object_or_404(
            DeliveryOrder, external_id=delivery_order_id
        )

        # facility isn't stored on the delivery; it lives on inward_record.
        # Validate the supplied facility actually owns this inward_record.
        if inward_record.facility_id != facility.id:
            return Response(
                {
                    "error": "Invalid input parameters",
                    "details": {
                        "facility_id": [
                            "Does not match the inward_record's facility"
                        ]
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- 409: delivery_order already linked (UNIQUE constraint) ---
        try:
            delivery = EAushadhiInwardRecordDelivery.objects.create(
                inward_record=inward_record,
                delivery_order=delivery_order,
                created_by=request.user,
                updated_by=request.user,
            )
        except IntegrityError:
            return Response(
                {"error": "delivery_order_id is already linked to an inward_record"},
                status=status.HTTP_409_CONFLICT,
            )

        # --- 201: created ---
        user_data = {
            "id": str(request.user.external_id),
            "username": request.user.username,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
        }
        return Response(
            {
                "id": str(delivery.external_id),
                "inward_record_id": str(delivery.inward_record.external_id),
                "delivery_order_id": str(delivery.delivery_order.external_id),
                "facility_id": str(facility.external_id),
                # "created_by": user_data,
                # "updated_by": user_data,
                "created_by": UserSpec.serialize(delivery.created_by).to_json(),
                "updated_by": UserSpec.serialize(delivery.updated_by).to_json(),
                "created_date": delivery.created_date.isoformat(),
                "modified_date": delivery.modified_date.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )