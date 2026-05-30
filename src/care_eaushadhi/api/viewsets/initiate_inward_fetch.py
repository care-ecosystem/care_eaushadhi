import datetime

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.models.facility import Facility
from care.utils.shortcuts import get_object_or_404

from care_eaushadhi.models.eaushadhi_institute_mapping import EAushadhiInstituteMapping
from care_eaushadhi.models.eaushadhi_institute_supplier_mapping import EAushadhiInstituteSupplierMapping
from care_eaushadhi.models.eaushadhi_fetch_log import FetchTriggeredBy

from care_eaushadhi.tasks import fetch_inward_from_eaushadi


class InitiateInwardFetchViewSet(GenericViewSet):
    # Overriding the default create API
    def create(self, request, *args, **kwargs):
        facility_id = request.data.get("facility_id")
        inward_date = request.data.get("inward_date")
        supplier_id = request.data.get("supplier_id")

        if not facility_id:
            raise ValidationError(
                {"facility_id": ["This field is required"]}
            )

        if not inward_date:
            raise ValidationError(
                {"inward_date": ["This field is required"]}
            )

        try:
            inward_date = datetime.datetime.strptime(
                inward_date, "%d/%m/%Y"
            ).date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Expected DD/MM/YYYY"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        facility = get_object_or_404(Facility, external_id=facility_id)

        institute_mapping = get_object_or_404(
            EAushadhiInstituteMapping,
            facility=facility
        )

        supplier_mapping_filters = {
            "institute_mapping": institute_mapping
        }

        if supplier_id:
            supplier_mapping_filters["supplier__external_id"] = supplier_id
        else:
            supplier_mapping_filters["is_default"] = True


        institute_supplier_mapping = get_object_or_404(
            EAushadhiInstituteSupplierMapping,
            **supplier_mapping_filters
        )

        task = fetch_inward_from_eaushadi.delay(
            facility_id=facility_id,
            inward_date=inward_date,
            supplier_id=institute_supplier_mapping.supplier.external_id,
            triggered_by=FetchTriggeredBy.USER.value
        )

        return Response(
            {
                "status": "processing",
                "task_id": task.id,
                "message": (
                    f"Fetch initiated. Poll /inward-records/"
                    f"?facility_id={facility_id}"
                    f"&inward_date={inward_date.isoformat()} to see results."
                ),
            },
            status=status.HTTP_202_ACCEPTED,
        )
