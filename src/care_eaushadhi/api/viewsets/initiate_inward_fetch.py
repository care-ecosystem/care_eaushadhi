import datetime
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.lock import Lock
from care.utils.shortcuts import get_object_or_404

from care_eaushadhi.models.eaushadhi_institute_mapping import EAushadhiInstituteMapping
from care_eaushadhi.models.eaushadhi_fetch_log import EAushadhiFetchLog, FetchStatus
from care_eaushadhi.models.eaushadhi_inward_record import EAushadhiInwardRecord, SyncStatus

from care_eaushadhi.tasks import fetch_inward_from_eaushadi


class InitiateInwardFetchViewSet(GenericViewSet):
    def authorize_fetch(self, facility):
        if not AuthorizationController.call(
            # "can_use_eaushadhi_integration",
            "can_write_supply_delivery",
            self.request.user,
            facility,
        ):
            raise PermissionDenied("You are not authorized to initiate fetch")

    # Overriding the default create API
    def create(self, request, *args, **kwargs):
        facility_id = request.data.get("facility_id")
        inward_date = request.data.get("inward_date")
        triggered_by = request.data.get("triggered_by")
        force_refresh = request.data.get("force_refresh", False)


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

        inward_date = inward_date.isoformat()

        facility = get_object_or_404(Facility, external_id=facility_id)

        # self.authorize_fetch(facility=facility)

        _ = get_object_or_404(
            EAushadhiInstituteMapping,
            facility=facility
        )

        with transaction.atomic(), Lock(f"eaushadhi-initiate-fetch:{facility_id}:{inward_date}"):
            existing_fetch_record = EAushadhiInwardRecord.objects.filter(
                facility = facility,
                inward_date = inward_date
            ).first()

            if existing_fetch_record:
                if existing_fetch_record.sync_status == SyncStatus.FETCHING:
                    return Response({
                        "status": "processing",
                        "message": "The data fetch is in progress"
                    }, status.HTTP_202_ACCEPTED)

                if existing_fetch_record.sync_status == SyncStatus.FETCHED and not force_refresh:
                    return Response({
                        "status": "Success",
                        "inward_record_id": existing_fetch_record.external_id,
                        "message": "Using cached data"
                    }, status.HTTP_202_ACCEPTED)

            inward_record, _ = EAushadhiInwardRecord.objects.update_or_create(
                facility=facility,
                inward_date=inward_date,
                defaults={
                    "sync_status": SyncStatus.FETCHING
                }
            )

            fetch_log = EAushadhiFetchLog.objects.create(
                facility=facility,
                inward_date=inward_date,
                triggered_by=triggered_by,
                fetch_status=FetchStatus.PENDING,
            )

            inward_record.last_attempted_fetch_log = fetch_log
            inward_record.save()

            task = fetch_inward_from_eaushadi.delay(
                fetch_log_id = fetch_log.external_id,
                inward_record_id = inward_record.external_id,
                facility_id = facility_id,
                inward_date = inward_date
            )

            return Response(
                {
                    "status": "processing",
                    "task_id": task.id,
                    "message": (
                        f"Fetch initiated. Poll /inward-records/"
                        f"?facility_id={facility_id}"
                        f"&inward_date={inward_date} to see results."
                    ),
                },
                status=status.HTTP_202_ACCEPTED,
            )
