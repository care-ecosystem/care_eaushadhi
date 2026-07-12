import csv
import logging
import sys

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Configuration ──────────────────────────────────────────────────────────────
BASE_URL    = "http://localhost:9000"           # Update before running
USERNAME    = "admin"                           # Update before running
PASSWORD    = "admin"                           # Update before running
FACILITY_ID = "e1ff13b6-383a-4217-a367-f421f7bbe478"               # Update before running
CSV_FILE    = "sample.csv"
# ───────────────────────────────────────────────────────────────────────────────


class TokenManager:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.access_token: str = ""
        self.refresh_token: str = ""

    def login(self) -> None:
        url = f"{self.base_url}/api/v1/auth/login/"
        response = requests.post(
            url, json={"username": self.username, "password": self.password}, timeout=30
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data.get("access", "")
        self.refresh_token = data.get("refresh", "")
        if not self.access_token:
            raise ValueError("Authentication response did not contain an access token.")
        logger.info("Login successful. Ready to process mappings.")

    def refresh(self) -> None:
        url = f"{self.base_url}/api/v1/auth/token/refresh/"
        response = requests.post(url, json={"refresh": self.refresh_token}, timeout=30)
        response.raise_for_status()
        data = response.json()
        self.access_token = data.get("access", "")
        if not self.access_token:
            raise ValueError("Token refresh response did not contain an access token.")
        logger.info("Session extended. Continuing import...")

    def auth_header(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}


def get_product_knowledge_id(base_url: str, token_manager: TokenManager, slug: str, facility_id: str) -> str:
    facility_slug = f"f-{facility_id}-{slug}"
    url = f"{base_url}/api/v1/product_knowledge/{facility_slug}/"
    params = {"facility": facility_id}
    response = requests.get(url, params=params, headers=token_manager.auth_header(), timeout=30)

    if response.status_code == 401:
        logger.info("Session expired — refreshing login and retrying the request.")
        token_manager.refresh()
        response = requests.get(url, params=params, headers=token_manager.auth_header(), timeout=30)

    response.raise_for_status()
    product_knowledge_id = response.json().get("id", "")
    if not product_knowledge_id:
        raise ValueError(f"No 'id' field in product knowledge response for slug '{slug}'.")
    return product_knowledge_id


def create_product_mapping(base_url: str, token_manager: TokenManager, facility_id: str, drug_id: str, drug_name: str, product_knowledge_id: str) -> dict:
    url = f"{base_url}/api/care_eaushadhi/product-mappings/"
    payload = {
        "facility_id": facility_id,
        "eaushadhi_drug_id": drug_id,
        "eaushadhi_drug_name": drug_name,
        "product_knowledge_id": product_knowledge_id,
        "mapping_type": "BULK_IMPORT",
    }
    response = requests.post(url, json=payload, headers=token_manager.auth_header(), timeout=30)

    if response.status_code == 401:
        logger.info("Session expired — refreshing login and retrying the request.")
        token_manager.refresh()
        response = requests.post(url, json=payload, headers=token_manager.auth_header(), timeout=30)

    response.raise_for_status()
    return response.json()


def process_csv(csv_file: str, base_url: str, token_manager: TokenManager, facility_id: str) -> None:
    required_columns = {"EAushadhi Drug ID", "EAushadhi Drug Name", "Product Knowledge Name", "Product Knowledge Slug"}
    success_count = 0
    error_count = 0

    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if not required_columns.issubset(set(reader.fieldnames or [])):
            missing = required_columns - set(reader.fieldnames or [])
            logger.error(
                "The CSV file is missing required column(s): %s. "
                "Please check the file and ensure all required columns are present.",
                ", ".join(sorted(missing)),
            )
            sys.exit(1)

        logger.info("CSV file opened successfully. Starting to process rows...")

        for line_number, row in enumerate(reader, start=2):
            drug_id = row.get("EAushadhi Drug ID", "").strip()
            drug_name = row.get("EAushadhi Drug Name", "").strip()
            product_knowledge_name = row.get("Product Knowledge Name", "").strip()
            product_knowledge_slug = row.get("Product Knowledge Slug", "").strip()

            if not drug_id or not drug_name or not product_knowledge_slug:
                missing_fields = [
                    field for field, val in [
                        ("EAushadhi Drug ID", drug_id),
                        ("EAushadhi Drug Name", drug_name),
                        ("Product Knowledge Slug", product_knowledge_slug),
                    ] if not val
                ]
                logger.warning(
                    "Row %d skipped — missing value(s) for: %s. Please fill in the missing data and re-run.",
                    line_number,
                    ", ".join(missing_fields),
                )
                error_count += 1
                continue

            try:
                product_knowledge_id = get_product_knowledge_id(base_url, token_manager, product_knowledge_slug, facility_id)
                result = create_product_mapping(base_url, token_manager, facility_id, drug_id, drug_name, product_knowledge_id)
                logger.info("Row %d: Mapping created successfully (ID: %s).", line_number, result.get("id", "N/A"))
                success_count += 1
            except requests.HTTPError as exc:
                reason = str(exc)
                if exc.response is not None:
                    try:
                        errors = exc.response.json().get("errors", [])
                        reason = errors[0]["msg"] if errors else exc.response.text
                    except Exception:
                        reason = exc.response.text
                logger.error("Row %d: Failed — %s", line_number, reason)
                error_count += 1
            except Exception as exc:
                logger.error("Row %d: Unexpected error — %s", line_number, exc)
                error_count += 1

    logger.info(
        "Import complete — %d row(s) succeeded, %d row(s) failed or skipped.",
        success_count, error_count,
    )


def main() -> None:
    logger.info("Starting eAushadhi product mapping import...")
    logger.info("Connecting to: %s", BASE_URL)

    token_manager = TokenManager(BASE_URL, USERNAME, PASSWORD)
    try:
        token_manager.login()
    except Exception as exc:
        logger.error("Login failed — please check your username, password, and server URL.")
        sys.exit(1)

    logger.info("Reading mappings from file: %s", CSV_FILE)
    process_csv(CSV_FILE, BASE_URL, token_manager, FACILITY_ID)


if __name__ == "__main__":
    main()
