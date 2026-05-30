from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def fetch_inward_from_eaushadi(facility_id, inward_date, supplier_id, triggered_by):
    logger.info("Celery Task Triggered: Fetching inward records from eAushadhi")
    pass
