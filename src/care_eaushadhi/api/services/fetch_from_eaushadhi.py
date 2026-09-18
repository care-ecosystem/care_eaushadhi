"""eAushadhi fetch and validation service.

This service integrates:
1. HTTP fetching from eAushadhi API
2. Response validation (via validators)
3. Response mapping to CARE format
"""

from datetime import date
import logging
import requests
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from care_eaushadhi.settings import plugin_settings as settings
from care_eaushadhi.api.validators import (
    KarnatakaResponseService,
    ValidationError,
)
from care_eaushadhi.api.validators.deployments.karnataka.service import ProcessingMetrics

logger = logging.getLogger(__name__)


class EAushadhiService:
    """Service for fetching and processing eAushadhi responses."""

    # =========================================================================
    # STAGE 1: Fetch from API
    # =========================================================================

    @staticmethod
    def fetch_from_eaushadhi(api_secret_key_code, inward_date):
        """Fetch raw response from eAushadhi API.
        
        Args:
            api_secret_key_code: Settings key for API credentials
            inward_date: ISO format date string (YYYY-MM-DD)
            
        Returns:
            {
                'status_code': int,
                'data': raw API response (list, empty list, or null)
            }
            
        Raises:
            requests.RequestException: On network/connection errors
        """
        inward_date_ddmmyyyy = date.fromisoformat(
            inward_date).strftime("%d/%m/%Y")
        
        try:
            url = settings.EAUSHADHI_API_ENDPOINT

            # Configure request-level retries for connection errors
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["POST"],
                raise_on_status=False
            )

            adapter = HTTPAdapter(max_retries=retry_strategy)
            session = requests.Session()
            session.mount("https://", adapter)
            session.mount("http://", adapter)

            # Configure proxy if provided
            proxies = {}
            if settings.EAUSHADHI_API_PROXY_HTTP:
                proxies['http'] = settings.EAUSHADHI_API_PROXY_HTTP
                logger.info("Using HTTP proxy: %s",
                            settings.EAUSHADHI_API_PROXY_HTTP)
            if settings.EAUSHADHI_API_PROXY_HTTPS:
                proxies['https'] = settings.EAUSHADHI_API_PROXY_HTTPS
                logger.info("Using HTTPS proxy: %s",
                            settings.EAUSHADHI_API_PROXY_HTTPS)

            headers = {
                'accept': 'application/json',
                'content-type': 'application/json',
                'authorization': f'Basic {getattr(settings, api_secret_key_code)}'
            }

            payload = {
                'InwardDate': inward_date_ddmmyyyy
            }

            # Use separate connect and read timeouts for better control
            connect_timeout = settings.EAUSHADHI_API_CONNECT_TIMEOUT
            read_timeout = settings.EAUSHADHI_API_READ_TIMEOUT
            timeout = (connect_timeout, read_timeout)

            verify_ssl = settings.EAUSHADHI_API_VERIFY_SSL

            logger.info(
                "Calling e-Aushadhi API | url=%s date=%s connect_timeout=%s read_timeout=%s verify_ssl=%s proxy=%s",
                url, inward_date_ddmmyyyy, connect_timeout, read_timeout, verify_ssl, bool(
                    proxies)
            )

            response = session.post(
                url=url,
                headers=headers,
                json=payload,
                timeout=timeout,
                proxies=proxies if proxies else None,
                verify=verify_ssl
            )

            logger.info(
                "e-Aushadhi API response received | status_code=%s date=%s",
                response.status_code, inward_date_ddmmyyyy
            )

            return {
                "status_code": response.status_code,
                "data": response.json(),
            }

        except requests.exceptions.ConnectTimeout as e:
            logger.error(
                "Connection timeout to e-Aushadhi API | url=%s timeout=%s error=%s",
                url, timeout, str(e)
            )
            raise
        except requests.exceptions.ReadTimeout as e:
            logger.error(
                "Read timeout from e-Aushadhi API | url=%s timeout=%s error=%s",
                url, timeout, str(e)
            )
            raise
        except requests.RequestException as e:
            logger.error(
                "Request failed to e-Aushadhi API | url=%s error_type=%s error=%s",
                url, type(e).__name__, str(e)
            )
            raise
        except Exception as e:
            logger.exception(
                "Unexpected error while fetching from e-Aushadhi | url=%s error=%s",
                url, str(e)
            )
            raise

    # =========================================================================
    # STAGE 2 & 3: Validate and Map (NEW - with Validator Integration)
    # =========================================================================

    @staticmethod
    def process_eaushadhi_response(raw_response, context, deployment=None):
        """
        Returns:
            Tuple of (mapped_items, validation_errors, metrics)
            - mapped_items: List of dicts ready for database
            - validation_errors: List of error dicts
            - metrics: ProcessingMetrics with duration, items_per_second, etc.
        """

        if deployment is None:
            deployment = settings.EAUSHADHI_DEPLOYMENT

        if not deployment:
            raise ValidationError(
                "Deployment not specified in settings",
                error_code="DEPLOYMENT_NOT_SPECIFIED"
            )
        
        logger.info("Current deployment settings is: %s", deployment)

        """⚡ Validate and map eAushadhi API response.
        
        VALIDATOR TRIGGERED HERE!
        
        Args:
            raw_response: Raw response from eAushadhi API
            context: Context dict with facility_id, inward_date, etc.
            deployment: Deployment name (default: 'karnataka')
            
        Returns:
            Tuple of (mapped_items, validation_errors)
            - mapped_items: List of dicts ready for database
            - validation_errors: List of error dicts
        """
        logger.info(
            "Starting response processing | deployment=%s",
            deployment
        )

        try:
            if deployment.lower() == "karnataka":
                service = KarnatakaResponseService()
                return service.process_response(raw_response, context)
            else:
                raise ValidationError(
                    f"Unknown deployment: {deployment}",
                    error_code="UNKNOWN_DEPLOYMENT"
                )


        except ValidationError as e:
            logger.warning("Validation failed: %s", e.to_dict())

            error_metrics = ProcessingMetrics(
                total_items=0,
                items_mapped=0,
                items_failed=1,
                # error_rate=1.0,
                duration_ms=0,
                items_per_second=0
            )
            return [], [e.to_dict()], error_metrics
        except Exception as e:
            logger.exception("Error processing response")
            error_metrics = ProcessingMetrics(
                total_items=0,
                items_mapped=0,
                items_failed=1,
                # error_rate=1.0,
                duration_ms=0,
                items_per_second=0
            )
            return [], [{
                "error_code": "PROCESSING_ERROR",
                "message": str(e),
                "details": {"exception_type": type(e).__name__}
            }], error_metrics