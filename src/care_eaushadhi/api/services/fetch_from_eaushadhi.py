from datetime import date
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from care_eaushadhi.settings import plugin_settings as settings

logger = logging.getLogger(__name__)

class EAushadhiService:

    @staticmethod
    def fetch_from_eaushadhi(api_secret_key_code, inward_date):
        inward_date_ddmmyyyy = date.fromisoformat(inward_date).strftime("%d/%m/%Y")
        response = None

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

            logger.info(
                "Calling e-Aushadhi API | url=%s date=%s connect_timeout=%s read_timeout=%s",
                url, inward_date_ddmmyyyy, connect_timeout, read_timeout
            )

            response = session.post(
                url=url,
                headers=headers,
                json=payload,
                timeout=timeout
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
