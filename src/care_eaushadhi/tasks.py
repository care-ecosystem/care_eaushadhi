import time
import logging
from datetime import date

from celery import shared_task
from django.db import transaction
import requests

from care.facility.models import Facility
from care.utils.shortcuts import get_object_or_404

from care_eaushadhi.models.eaushadhi_fetch_log import EAushadhiFetchLog, FetchStatus
from care_eaushadhi.models.eaushadhi_inward_record import EAushadhiInwardRecord, SyncStatus
from care_eaushadhi.models.eaushadhi_institute_mapping import EAushadhiInstituteMapping
from care_eaushadhi.models.eaushadhi_inward_record_item import EAushadhiInwardRecordItem, InwardRecordItemStatus
from care_eaushadhi.api.services.fetch_from_eaushadhi import EAushadhiService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def fetch_inward_from_eaushadi(
    self,
    fetch_log_id,
    inward_record_id,
    facility_id,
    inward_date,
):
    logger.info(
        "Celery Task Triggered: fetch_inward_from_eaushadi | "
        "fetch_log_id=%s facility_id=%s inward_date=%s attempt=%s",
        fetch_log_id, facility_id, inward_date, self.request.retries + 1,
    )

    fetch_log = get_object_or_404(EAushadhiFetchLog, external_id=fetch_log_id)
    inward_record = get_object_or_404(EAushadhiInwardRecord, external_id=inward_record_id)
    facility = get_object_or_404(Facility, external_id=facility_id)
    institute_mapping = get_object_or_404(EAushadhiInstituteMapping, facility=facility)

    start_ms = int(time.time() * 1000)

    try:
        logger.info("Calling EAushadhiService.fetch_from_eaushadhi for inward_date=%s", inward_date)
        response = EAushadhiService.fetch_from_eaushadhi(
            api_secret_key_code=institute_mapping.credentials_ref,
            inward_date=inward_date,
        )
    except requests.RequestException as exc:
        retry_countdown = 5 * (3 ** self.request.retries)
        logger.warning(
            "Network error calling eAushadi API (attempt %s), retrying in %ss: %s",
            self.request.retries + 1, retry_countdown, exc,
        )
        raise self.retry(exc=exc, countdown=retry_countdown)
    except Exception as exc:
        logger.exception("Unhandled error in fetch_inward_from_eaushadi")
        _mark_failed(
            fetch_log, inward_record,
            http_status_code=None,
            error_code="UNHANDLED_EXCEPTION",
            error_detail=str(exc),
        )
        raise  # still let Celery retry/fail the task

    try:

        elapsed_ms = int(time.time() * 1000) - start_ms
        status_code = response.get("status_code")
        data = response.get("data")


        if status_code != 200:
            logger.warning(
                "eAushadi API returned non-200 status | status_code=%s facility=%s date=%s",
                status_code, facility_id, inward_date,
            )
            _mark_failed(
                fetch_log, inward_record,
                http_status_code=status_code,
                error_code="HTTP_ERROR",
                error_detail=f"Unexpected status code: {status_code}",
            )
            return


        if not isinstance(data, list):
            logger.warning(
                "Unexpected eAushadi response shape | expected list got %s | facility=%s date=%s",
                type(data).__name__, facility_id, inward_date,
            )
            _mark_failed(
                fetch_log, inward_record,
                http_status_code=status_code,
                error_code="UNEXPECTED_RESPONSE_SHAPE",
                error_detail=f"Expected list, got {type(data).__name__}: {str(data)[:200]}",
            )
            return

        # ── 4c. Schema validation (wire in once validator exists) ─────────────────
        # is_valid, error_info = validate_inward_response_schema(data)
        # if not is_valid:
        #     logger.warning("Schema validation failed: %s", error_info)
        #     _mark_failed(fetch_log, inward_record, http_status_code=status_code,
        #                  error_code="SCHEMA_VALIDATION_ERROR", error_detail=str(error_info))
        #     return  # No retry — deterministic failure


        institute_id = institute_mapping.eaushadhi_institute_id
        items_from_api = [
            item for item in data
            if str(item.get("instituteid")) == str(institute_id)
        ]
        logger.info(
            "Items after institute filter | institute_id=%s total=%d filtered=%d",
            institute_id, len(data), len(items_from_api),
        )


        with transaction.atomic():
            existing_items = EAushadhiInwardRecordItem.objects.filter(
                inward_record=inward_record
            ).select_for_update()

            existing_lookup = {
                (item.inward_no, item.drug_id, item.batch_no): item
                for item in existing_items
            }

            api_keys = set()
            upsert_list = []

            for api_item in items_from_api:
                inward_no = api_item.get("inwardno")
                drug_id = api_item.get("Drug_id")
                batch_no = api_item.get("Batch_number")
                manufactured_date = _parse_date(api_item.get("Mfg_date"))
                expiry_date = _parse_date(api_item.get("Exp_date"))
                receipt_date = _parse_date(api_item.get("Receipt_Date"))
                unit_pack_raw = api_item.get("UnitPack", "")
                unit_pack = _parse_unit_pack(unit_pack_raw)
                drug_name=api_item.get("Drug_name", "")
                dose = api_item.get("Dose", "")
                quantity_in_units = api_item.get("Quantity_In_Units", 0)
                quantity_received_current = api_item.get("Quantity_In_Pack", 0)
                warehouse_name = api_item.get("Warehouse_name", "")


                key = ( inward_no, drug_id, batch_no )
                api_keys.add(key)

                if key in existing_lookup:
                    db_item = existing_lookup[key]
                    db_item.drug_name = drug_name
                    db_item.manufactured_date = manufactured_date
                    db_item.expiry_date = expiry_date
                    db_item.receipt_date = receipt_date
                    db_item.unit_pack = unit_pack
                    db_item.unit_pack_raw = unit_pack_raw
                    db_item.dose = dose
                    db_item.quantity_in_units = quantity_in_units
                    db_item.quantity_received_current = quantity_received_current
                    db_item.warehouse_name = warehouse_name
                    db_item.status = InwardRecordItemStatus.ACTIVE
                    db_item.current_fetch_log = fetch_log
                    upsert_list.append(db_item)
                else:
                    upsert_list.append(
                        EAushadhiInwardRecordItem(
                            inward_record=inward_record,
                            inward_no=inward_no,
                            drug_id=drug_id,
                            drug_name=drug_name,
                            batch_no=batch_no,
                            manufactured_date=manufactured_date,
                            expiry_date=expiry_date,
                            receipt_date=receipt_date,
                            unit_pack=unit_pack,
                            unit_pack_raw=unit_pack_raw,
                            dose=dose,
                            quantity_in_units=quantity_in_units,
                            quantity_received_initial=quantity_in_units,
                            quantity_received_current=quantity_received_current,
                            warehouse_name=warehouse_name,
                            status=InwardRecordItemStatus.ACTIVE,
                            initial_fetch_log=fetch_log,
                            current_fetch_log=fetch_log,
                        )
                    )

            discrepant_keys = set(existing_lookup.keys()) - api_keys
            for key in discrepant_keys:
                db_item = existing_lookup[key]
                db_item.status = InwardRecordItemStatus.INACTIVE
                db_item.current_fetch_log = fetch_log
                upsert_list.append(db_item)

            EAushadhiInwardRecordItem.objects.bulk_create(
                [i for i in upsert_list if i.pk is None],
                ignore_conflicts=False,
            )
            EAushadhiInwardRecordItem.objects.bulk_update(
                [i for i in upsert_list if i.pk is not None],
                fields=[
                    "drug_name",
                    "manufactured_date",
                    "expiry_date",
                    "receipt_date",
                    "unit_pack",
                    "unit_pack_raw",
                    "dose",
                    "quantity_in_units",
                    "quantity_received_current",
                    "warehouse_name",
                    "status",
                    "current_fetch_log",
                ],
            )

            fetch_log.fetch_status = FetchStatus.SUCCESS
            fetch_log.http_status_code = status_code
            fetch_log.api_response_time_ms = elapsed_ms
            fetch_log.total_items_in_response = len(data)
            fetch_log.retry_count = self.request.retries

            fetch_log.save(
                update_fields=[
                    "fetch_status",
                    "http_status_code",
                    "api_response_time_ms",
                    "total_items_in_response",
                    "retry_count",
                ]
            )


            inward_record.sync_status = SyncStatus.FETCHED
            inward_record.last_successful_fetch_log = fetch_log

            if inward_record.items_initial_count is None:
                inward_record.items_initial_count = len(items_from_api)

            inward_record.items_current_count = EAushadhiInwardRecordItem.objects.filter(
                inward_record=inward_record,
                status=InwardRecordItemStatus.ACTIVE,
            ).count()

            inward_record.save(
                update_fields=[
                    "sync_status",
                    "last_successful_fetch_log",
                    "items_initial_count",
                    "items_current_count",
                ]
            )
    except Exception as exc:
        logger.exception(
            "Error processing eAushadi response | facility=%s date=%s",
            facility_id, inward_date,
        )
        _mark_failed(
            fetch_log, inward_record,
            http_status_code=None,
            error_code="PROCESSING_ERROR",
            error_detail=str(exc),
        )
        raise  # let Celery mark the task as failed

    logger.info(
        "fetch_inward_from_eaushadi completed | inward_record=%s items=%d elapsed_ms=%d",
        inward_record_id, len(items_from_api), elapsed_ms,
    )


def _mark_failed(fetch_log, inward_record, http_status_code, error_code, error_detail):
    try:
        fetch_log.fetch_status = FetchStatus.FAILURE
        fetch_log.http_status_code = http_status_code
        fetch_log.error_code = error_code
        fetch_log.error_message = f"Fetch failed with error_code={error_code}"
        fetch_log.error_detail = error_detail
        fetch_log.save(
            update_fields=[
                "fetch_status",
                "http_status_code",
                "error_code",
                "error_message",
                "error_detail"
            ]
        )
    except Exception:
        logger.exception("Failed to update fetch_log during failure marking")

    try:
        inward_record.sync_status = SyncStatus.FAILED
        inward_record.save(update_fields=["sync_status"])
    except Exception:
        logger.exception("Failed to update inward_record during failure marking")


def _parse_date(value: str | None) -> date | None:
    """Parse YYYY-MM-DD date strings from the API. Returns None on any failure."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        logger.warning("Could not parse date: %r", value)
        return None


def _parse_unit_pack(raw: str) -> float:
    """
    Convert UnitPack strings like "1x10x10" to a numeric value by multiplying
    all parts. Falls back to 1.0 if unparseable.
    """
    if not raw:
        return 1.0
    try:
        parts = [float(p) for p in raw.lower().split("x") if p.strip()]
        result = 1.0
        for p in parts:
            result *= p
        return result
    except (ValueError, TypeError):
        logger.warning("Could not parse UnitPack: %r, defaulting to 1.0", raw)
        return 1.0
