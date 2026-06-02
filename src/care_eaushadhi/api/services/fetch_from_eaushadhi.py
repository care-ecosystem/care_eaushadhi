from datetime import date
import logging
import requests

from care_eaushadhi.settings import plugin_settings as settings

logger = logging.getLogger(__name__)

class EAushadhiService:

    @staticmethod
    def fetch_from_eaushadhi(api_secret_key_code, inward_date):
        inward_date_ddmmyyyy = date.fromisoformat(inward_date).strftime("%d/%m/%Y")

        logger.info("Fetching data from e-Aushadhi API for date: %s", inward_date_ddmmyyyy)
        logger.info("Using e-Aushadhi API endpoint: %s", settings.EAUSHADHI_API_ENDPOINT)
        logger.info("Using API secret key code: %s", api_secret_key_code)

        response = None

        try:
            url = settings.EAUSHADHI_API_ENDPOINT

            headers = {
                'accept': 'application/json',
                'content-type': 'application/json',
                'authorization': f'Basic {getattr(settings, api_secret_key_code)}'
            }

            payload = {
                'InwardDate': inward_date_ddmmyyyy
            }

            response = requests.post(
                url=url,
                headers=headers,
                json=payload,
                timeout=30
            )

            logger.info("Received response from e-Aushadhi API with status code: %s", response.status_code)
            logger.debug("Response content: %s", response.text)

            return {
                "status_code": response.status_code,
                "data": response.json(),
            }
        except requests.RequestException:
            logger.exception("Failed to fetch from e-Aushadhi")
            raise
        except Exception as e:
            logger.exception("An unexpected error occurred while fetching from e-Aushadhi: %s", str(e))
            raise
