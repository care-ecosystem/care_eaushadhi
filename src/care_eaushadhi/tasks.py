from decimal import Decimal
import time
import logging
import json
from datetime import date

from celery import shared_task
from django.db import transaction
import requests

from care.facility.models import Facility
from care.users.models import User
from care.utils.shortcuts import get_object_or_404

from care_eaushadhi.models.eaushadhi_fetch_log import EAushadhiFetchLog, FetchStatus
from care_eaushadhi.models.eaushadhi_inward_record import EAushadhiInwardRecord, SyncStatus
from care_eaushadhi.models.eaushadhi_institute_mapping import EAushadhiInstituteMapping
from care_eaushadhi.models.eaushadhi_inward_record_item import EAushadhiInwardRecordItem, InwardRecordItemStatus
from care_eaushadhi.api.services.fetch_from_eaushadhi import EAushadhiService
from care_eaushadhi.settings import plugin_settings as settings

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="care_eaushadhi.tasks.fetch_inward_from_eaushadi",
    max_retries=int(settings.EAUSHADHI_API_RETRY_COUNT),
    default_retry_delay=5,
    autoretry_for=(requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def fetch_inward_from_eaushadi(
    self,
    fetch_log_id,
    inward_record_id,
    facility_id,
    inward_date,
    user_id
):
    max_retries = int(self.max_retries) if isinstance(self.max_retries, str) else self.max_retries

    logger.info(
        "Celery Task Triggered: fetch_inward_from_eaushadi | "
        "fetch_log_id=%s facility_id=%s inward_date=%s attempt=%s",
        fetch_log_id, facility_id, inward_date, self.request.retries + 1,
    )

    fetch_log = get_object_or_404(EAushadhiFetchLog, external_id=fetch_log_id)
    inward_record = get_object_or_404(EAushadhiInwardRecord, external_id=inward_record_id)
    facility = get_object_or_404(Facility, external_id=facility_id)
    institute_mapping = get_object_or_404(EAushadhiInstituteMapping, facility=facility)
    user = get_object_or_404(User, external_id=user_id)

    inward_record.last_attempted_fetch_log = fetch_log
    inward_record.save(update_fields=["last_attempted_fetch_log"])

    start_ms = int(time.time() * 1000)

    try:
        logger.info(
            "Calling EAushadhiService.fetch_from_eaushadhi | inward_date=%s attempt=%s/%s",
            inward_date, self.request.retries + 1, max_retries + 1
        )
        response = EAushadhiService.fetch_from_eaushadhi(
            api_secret_key_code=institute_mapping.credentials_ref,
            inward_date=inward_date,
        )
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout) as exc:
        if self.request.retries >= max_retries:
            logger.error(
                "Max retries exhausted for eAushadi fetch due to timeout | "
                "facility=%s date=%s attempts=%s error=%s",
                facility_id, inward_date, self.request.retries + 1, str(exc)
            )

            _mark_failed(
                fetch_log, inward_record,
                http_status_code=None,
                error_code="TIMEOUT_ERROR",
                error_detail=f"Connection/Read timeout after {self.request.retries + 1} attempts: {str(exc)}",
                user=user
            )
            raise

        # Use exponential backoff with jitter: 5, 15, 45 seconds
        retry_countdown = 5 * (3 ** self.request.retries)

        logger.warning(
            "Timeout calling eAushadi API (attempt %s/%s), retrying in %ss | error=%s",
            self.request.retries + 1, max_retries + 1, retry_countdown, type(exc).__name__,
        )

        raise self.retry(exc=exc, countdown=retry_countdown) from exc
    except requests.RequestException as exc:
        if self.request.retries >= max_retries:
            logger.error(
                "Max retries exhausted for eAushadi fetch | facility=%s date=%s attempts=%s error=%s",
                facility_id, inward_date, self.request.retries + 1, str(exc)
            )

            _mark_failed(
                fetch_log, inward_record,
                http_status_code=None,
                error_code="NETWORK_ERROR",
                error_detail=f"Network error after {self.request.retries + 1} attempts: {str(exc)}",
                user=user
            )
            raise

        retry_countdown = 5 * (3 ** self.request.retries)

        logger.warning(
            "Network error calling eAushadi API (attempt %s/%s), retrying in %ss | error_type=%s error=%s",
            self.request.retries + 1, max_retries + 1, retry_countdown, type(exc).__name__, str(exc)
        )

        raise self.retry(exc=exc, countdown=retry_countdown) from exc
    except Exception as exc:
        logger.exception("Unhandled error in fetch_inward_from_eaushadi")
        _mark_failed(
            fetch_log, inward_record,
            http_status_code=None,
            error_code="UNHANDLED_EXCEPTION",
            error_detail=str(exc),
            user=user
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
                error_detail=json.dumps(response),
                user=user
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
                error_detail=json.dumps(response),
                user=user
            )
            return


        institute_id = institute_mapping.eaushadhi_institute_id
        items_from_api = [
            item for item in data
            if str(item.get("instituteid")) == str(institute_id)
        ]
        logger.info(
            "Items after institute filter | institute_id=%s total=%d filtered=%d",
            institute_id, len(data), len(items_from_api),
        )

        logger.info("🔍 Starting validation and mapping...")
        deployment = settings.EAUSHADHI_DEPLOYMENT
        
        try:
            context = {
                'inward_date': inward_date,
                'facility_id': str(facility_id),
                'eaushadhi_institute_id': institute_id,
            }
            
            mapped_items, validation_errors = EAushadhiService.process_eaushadhi_response(
                raw_response=items_from_api,
                context=context,
                deployment=deployment
            )
            
            logger.info(
                "✓ Validation complete | valid=%d errors=%d",
                len(mapped_items), len(validation_errors)
            )
            
            if validation_errors:
                logger.warning(f"⚠️  {len(validation_errors)} validation errors:")
                error = validation_errors[0]
                _mark_failed(
                    fetch_log=fetch_log,
                    inward_record=inward_record,
                    http_status_code=status_code,
                    error_code=error.get("error_code", "VALIDATION_ERROR"),
                    error_detail=error.get("message"),
                    user=user
                )

            return
        
        except Exception as e:
            logger.exception("❌ Validator failed: %s", str(e))
            _mark_failed(
                fetch_log, inward_record,
                http_status_code=status_code,
                error_code="VALIDATOR_ERROR",
                error_detail=str(e),
                user=user
            )
            raise
        
        # Use validated items instead of raw API items
        items_from_api = mapped_items

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

            for mapped_item in items_from_api:
                # Extract from mapped/validated format
                metadata = mapped_item.get("metadata", {})
                
                inward_no = mapped_item.get("eaushadhi_inwardno")
                drug_id = metadata.get("drug_id")
                batch_no = metadata.get("batch_number")
                manufactured_date = _parse_date(metadata.get("mfg_date"))
                expiry_date = _parse_date(metadata.get("exp_date"))
                receipt_date = _parse_date(metadata.get("receipt_date"))
                unit_pack_raw = mapped_item.get("unit_pack", "")
                unit_pack = _parse_unit_pack(unit_pack_raw)
                drug_name = metadata.get("drug_name", "")
                dose = metadata.get("dose", "")
                quantity_in_units = mapped_item.get("quantity_in_units", 0)
                quantity_received_current = mapped_item.get("quantity_in_pack", 0)
                warehouse_name = metadata.get("warehouse_name", "")


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
                    db_item.updated_by = user
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
                            created_by=user,
                            updated_by=user,
                        )
                    )

            discrepant_keys = set(existing_lookup.keys()) - api_keys
            for key in discrepant_keys:
                db_item = existing_lookup[key]
                db_item.status = InwardRecordItemStatus.INACTIVE
                db_item.current_fetch_log = fetch_log
                db_item.updated_by = user
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
                    "updated_by",
                ],
            )

            fetch_log.fetch_status = FetchStatus.SUCCESS
            fetch_log.http_status_code = status_code
            fetch_log.api_response_time_ms = elapsed_ms
            fetch_log.total_items_in_response = len(data)
            fetch_log.retry_count = self.request.retries
            fetch_log.updated_by = user
            fetch_log.response_payload = response

            fetch_log.save(
                update_fields=[
                    "fetch_status",
                    "http_status_code",
                    "api_response_time_ms",
                    "total_items_in_response",
                    "retry_count",
                    "updated_by",
                    "response_payload"
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

            inward_record.updated_by = user

            inward_record.save(
                update_fields=[
                    "sync_status",
                    "last_successful_fetch_log",
                    "items_initial_count",
                    "items_current_count",
                    "updated_by",
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
            user=user
        )
        raise  # let Celery mark the task as failed

    logger.info(
        "fetch_inward_from_eaushadi completed | inward_record=%s items=%d elapsed_ms=%d",
        inward_record_id, len(items_from_api), elapsed_ms,
    )


def _mark_failed(fetch_log, inward_record, http_status_code, error_code, error_detail, user = None):
    try:
        fetch_log.fetch_status = FetchStatus.FAILURE
        fetch_log.http_status_code = http_status_code
        fetch_log.error_code = error_code
        fetch_log.error_message = f"Fetch failed with error_code={error_code}"
        fetch_log.error_detail = error_detail
        fetch_log.updated_by = user

        fetch_log.save(
            update_fields=[
                "fetch_status",
                "http_status_code",
                "error_code",
                "error_message",
                "error_detail",
                "updated_by"
            ]
        )
    except Exception:
        logger.exception("Failed to update fetch_log during failure marking")

    try:
        inward_record.sync_status = SyncStatus.FAILED
        inward_record.updated_by = user
        inward_record.save(update_fields=["sync_status", "updated_by"])
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


def _parse_unit_pack(raw: str) -> Decimal:
    """
    Convert UnitPack strings like "1x10x10" to a numeric value by multiplying
    all parts. Falls back to 1.0 if unparseable.
    """
    if not raw:
        return Decimal("1")
    try:
        parts = [Decimal(p) for p in raw.lower().split("x") if p.strip()]
        result = Decimal("1")
        for p in parts:
            result *= p
        return result
    except (ValueError, TypeError, ArithmeticError):
        logger.warning("Could not parse UnitPack: %r, defaulting to 1.0", raw)
        return Decimal("1")