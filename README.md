# Care eAushadhi Backend Plugin

[![Version](https://img.shields.io/badge/version-1.0.0--BETA-blue.svg)](https://github.com/ohcnetwork/care_eaushadhi)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-4.2%2B-green.svg)](https://www.djangoproject.com/)
[![eGov Foundation](https://img.shields.io/badge/eGov-Foundation-orange.svg)](https://egov.org.in)

Care eAushadhi is a backend plugin for the CARE platform to integrate with India's eAushadhi platform (National Health Authority). This plugin enables seamless synchronization of pharmaceutical stock inward records from eAushadhi warehouses into CARE's inventory management system.

**Developed by**: [eGov Foundation](https://egov.org.in)

## Quick Links

- 📐 **Tech & Product Design**: [Design Documentation](https://care-ecosystem.github.io/Designs/features/eaushadhi-v2/index.html)
- 🖥️ **Frontend Plugin**: [care_eaushadhi_fe](https://github.com/care-ecosystem/care_eaushadhi_fe)
- 🐛 **Report Issues**: [GitHub Issues](https://github.com/ohcnetwork/care_eaushadhi/issues)
- 📖 **CARE Platform**: [care.ohc.network](https://care.ohc.network)
- 🏢 **eGov Foundation**: [egov.org.in](https://egov.org.in)
- 📧 **Contact**: [jagan.kumar@egovernments.org](mailto:jagan.kumar@egovernments.org)

## Overview

The eAushadhi Backend Plugin provides the server-side API infrastructure for integrating eAushadhi (India's national e-pharmacy platform) with CARE. It handles authentication, data fetching, transformation, and storage of pharmaceutical inward records from eAushadhi into CARE's inventory system.

This plugin was developed as part of the eGov Foundation's initiative to enhance healthcare digitization in India. The current version (v1.0.0-BETA) is specifically configured for Karnataka state deployments, with plans to generalize the solution for nationwide adoption across all state eAushadhi implementations.

## Features

### Core Functionality

- **Institute Mapping System**
  - Link CARE facilities to eAushadhi institute IDs
  - Map CARE suppliers/organizations to eAushadhi warehouse names
  - Configure default suppliers for automated selection
  - Schema version management for API compatibility
  - Secure credentials management via encrypted references

- **Product Mapping System**
  - Map eAushadhi drug IDs to CARE's product knowledge base
  - Support multiple mappings per drug for flexibility
  - Search and fuzzy matching capabilities
  - Metadata storage for additional context

- **Inward Record Management**
  - Fetch inward records from eAushadhi API in real-time
  - Store inward records with complete item details
  - Track batch numbers, expiry dates, and pack sizes
  - Link inward records to CARE delivery orders
  - Status tracking and error logging

- **Workflow Control**
  - Admin-configurable workflow permissions via meta flags:
    - `disable_inward_date` - Lock inward date to today
    - `manual_addition` - Allow manual item addition
    - `allow_deleting_inward_after_fetch` - Control deletion of fetched records
    - `allow_updating_quantity_after_received` - Control quantity editing after receipt

- **API Integration**
  - RESTful API endpoints for all operations
  - Polling mechanism for async inward fetching
  - Comprehensive error handling and retry logic
  - Request/response logging for audit trail

### Admin Features

- **Institute Mapping Administration**
  - Create and manage facility-to-institute mappings
  - Configure supplier-to-warehouse mappings
  - Set default suppliers
  - Manage API credentials securely
  - Update workflow permissions

- **Audit Trail**
  - Track all create, update, and delete operations
  - Store created_by and updated_by information
  - Timestamp all operations
  - Soft delete support for data recovery

## Installation

### Prerequisites

- CARE backend installed and running
- Python 3.10 or higher
- PostgreSQL database (via CARE)
- Redis (via CARE)

### Production Installation

To install care_eaushadhi in production, add the plugin config in [care/plug_config.py](https://github.com/ohcnetwork/care/blob/develop/plug_config.py):

```python
from plugs.manager import PlugManager
from plugs.plug import Plug

care_eaushadhi_plug = Plug(
    name="care_eaushadhi",
    package_name="git+https://github.com/ohcnetwork/care_eaushadhi.git",
    version="@main",
    configs={
        # eAushadhi API Configuration (Karnataka-specific)
        "EAUSHADHI_API_ENDPOINT": "https://aushada.karnataka.gov.in/e-services/api/instinward/eGovuser",
        "EAUSHADHI_API_SECRET_KEY": "your-base64-encoded-credentials",  # Base64 encoded credentials
        "EAUSHADHI_API_RETRY_COUNT": 5,
        "EAUSHADHI_API_TIMEOUT": 30,
        "EAUSHADHI_API_CONNECT_TIMEOUT": 10,
        "EAUSHADHI_API_READ_TIMEOUT": 30,
        "EAUSHADHI_API_VERIFY_SSL": True,

        # Optional: Proxy settings
        # "EAUSHADHI_API_PROXY_HTTP": "",
        # "EAUSHADHI_API_PROXY_HTTPS": "",

        # Product mapping similarity threshold (0.0 to 1.0)
        # "SIMILARITY_THRESHOLD": 0.2,
    },
)

plugs = [care_eaushadhi_plug]
manager = PlugManager(plugs)
```

### Local Development Setup

1. **Clone CARE backend**:
   ```bash
   git clone https://github.com/ohcnetwork/care.git
   cd care
   ```

2. **Clone the plugin inside CARE**:
   ```bash
   git clone https://github.com/ohcnetwork/care_eaushadhi.git
   ```

3. **Configure the plugin in `plug_config.py`**:
   ```python
   from plugs.manager import PlugManager
   from plugs.plug import Plug

   care_eaushadhi_plugin = Plug(
       name="care_eaushadhi",
       package_name="/app/care_eaushadhi",  # Docker path
       version="",  # Empty for local development
       configs={},
   )

   plugs = [care_eaushadhi_plugin]
   manager = PlugManager(plugs)
   ```

4. **Modify `plugs/manager.py` for editable installation**:
   ```python
   # Add -e flag for editable mode
   subprocess.check_call(
       [sys.executable, "-m", "pip", "install", "-e", *packages]
   )
   ```

5. **Rebuild and start Docker containers**:
   ```bash
   make re-build
   make up
   ```

6. **Run migrations**:
   ```bash
   docker-compose exec backend python manage.py migrate care_eaushadhi
   ```

7. **Verify installation**:
   ```bash
   docker-compose exec backend python manage.py shell
   ```
   ```python
   >>> from django.conf import settings
   >>> print('care_eaushadhi' in settings.INSTALLED_APPS)
   True
   >>> from care_eaushadhi.models import EAushadhiInstituteMapping
   >>> print("Plugin installed successfully!")
   ```

> [!IMPORTANT]
> Do not push local development changes (editable mode configuration) in a PR. These changes are only for local development.

For detailed development setup, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Configuration

### Environment Variables

The following configuration variables are available for care_eaushadhi:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `EAUSHADHI_API_ENDPOINT` | eAushadhi API endpoint URL (Karnataka-specific) | `https://aushada.karnataka.gov.in/e-services/api/instinward/eGovuser` | No |
| `EAUSHADHI_API_SECRET_KEY` | Base64 encoded credentials for eAushadhi API | `base_encoded_secret_key` | No |
| `EAUSHADHI_API_RETRY_COUNT` | Maximum retry attempts for failed API calls | `5` | No |
| `EAUSHADHI_API_TIMEOUT` | Overall API request timeout in seconds | `30` | No |
| `EAUSHADHI_API_CONNECT_TIMEOUT` | Connection timeout in seconds | `10` | No |
| `EAUSHADHI_API_READ_TIMEOUT` | Read timeout in seconds | `30` | No |
| `EAUSHADHI_API_VERIFY_SSL` | Verify SSL certificates for API calls | `True` | No |
| `EAUSHADHI_API_PROXY_HTTP` | HTTP proxy URL (if needed) | `""` (empty) | No |
| `EAUSHADHI_API_PROXY_HTTPS` | HTTPS proxy URL (if needed) | `""` (empty) | No |
| `SIMILARITY_THRESHOLD` | Similarity threshold for product mapping (0.0 to 1.0) | `0.2` | No |

**Note**: All variables can be overridden via environment variables. The plugin will check PLUGIN_CONFIGS first, then environment variables, then fall back to defaults.

### Database Models

The plugin creates the following database tables:

- `care_eaushadhi_institute_mapping` - Facility to eAushadhi institute mappings
- `care_eaushadhi_institute_supplier_mapping` - Supplier to warehouse mappings
- `care_eaushadhi_product_mapping` - Drug ID to product mappings
- `care_eaushadhi_inward_record` - Inward records from eAushadhi
- `care_eaushadhi_inward_record_item` - Individual items in inward records
- `care_eaushadhi_inward_record_delivery` - Links to CARE delivery orders
- `care_eaushadhi_inward_record_item_delivery` - Links to CARE delivery items
- `care_eaushadhi_fetch_log` - Fetch request audit trail
- `care_eaushadhi_api_schema` - API schema version tracking

All tables use the `care_eaushadhi_` prefix to avoid conflicts with core CARE tables.

## API Endpoints

### Institute Mapping APIs

- `POST /api/care_eaushadhi/institute-mappings/` - Create institute mapping
- `GET /api/care_eaushadhi/institute-mappings/` - List institute mappings
- `GET /api/care_eaushadhi/institute-mappings/{id}/` - Retrieve institute mapping
- `PATCH /api/care_eaushadhi/institute-mappings/{id}/` - Update institute mapping

**Filters**: `facility_id`, `eaushadhi_institute_id`, `schema_version`

**Documentation**: See [docs/INSTITUTE_MAPPING_CREATE_API.md](docs/INSTITUTE_MAPPING_CREATE_API.md) and [docs/INSTITUTE_MAPPING_UPDATE_API.md](docs/INSTITUTE_MAPPING_UPDATE_API.md)

### Product Mapping APIs

- `POST /api/care_eaushadhi/product-mappings/search/` - Search product mappings by drug ID

### Inward Fetch APIs

- `POST /api/care_eaushadhi/initiate-inward-fetch/` - Initiate inward fetch from eAushadhi
  - Requires: delivery order ID
  - Returns: fetch status and polling information
  - Supports: async polling with status updates

### Inward Record APIs

- `GET /api/care_eaushadhi/inward-records/` - List inward records
- `GET /api/care_eaushadhi/inward-records/{id}/` - Retrieve inward record details

### Delivery Record APIs

- `POST /api/care_eaushadhi/record-deliveries/` - Create delivery record
- `GET /api/care_eaushadhi/record-deliveries/` - List delivery records
- `GET /api/care_eaushadhi/record-deliveries/{id}/` - Retrieve delivery record

### Record Item Delivery APIs

- `POST /api/care_eaushadhi/record-item-deliveries/` - Create item delivery record

For detailed API documentation with request/response examples, see the [docs/](docs/) directory.

## Dependencies

### Required Backend Plugins

This plugin works in conjunction with:

- **CARE Platform** - Base healthcare platform
- **super_batch_request** (optional) - For batch API operations from frontend

### Python Dependencies

- Django >= 4.2
- djangorestframework >= 3.14
- pydantic >= 2.0
- requests (for eAushadhi API calls)

All dependencies are managed via `setup.py`.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      CARE Backend (Django)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              care_eaushadhi (This Plugin)              │   │
│  │                                                         │   │
│  │  ┌──────────────────────────────────────────────────┐  │   │
│  │  │  API Layer (Django REST Framework)              │  │   │
│  │  │  • Institute Mapping ViewSets                    │  │   │
│  │  │  • Product Mapping ViewSets                      │  │   │
│  │  │  • Inward Fetch ViewSets                         │  │   │
│  │  │  • Delivery Record ViewSets                      │  │   │
│  │  └──────────────────┬───────────────────────────────┘  │   │
│  │                     │                                   │   │
│  │  ┌──────────────────▼───────────────────────────────┐  │   │
│  │  │  Business Logic Layer                            │  │   │
│  │  │  • Pydantic Validation (Specs)                   │  │   │
│  │  │  • Data Transformation                           │  │   │
│  │  │  • Workflow Control                              │  │   │
│  │  └──────────────────┬───────────────────────────────┘  │   │
│  │                     │                                   │   │
│  │  ┌──────────────────▼───────────────────────────────┐  │   │
│  │  │  Data Layer (Django ORM)                         │  │   │
│  │  │  • Models (EMRBaseModel)                         │  │   │
│  │  │  • Database Operations                           │  │   │
│  │  │  • Audit Trail                                   │  │   │
│  │  └──────────────────┬───────────────────────────────┘  │   │
│  │                     │                                   │   │
│  │  ┌──────────────────▼───────────────────────────────┐  │   │
│  │  │  External Integration Layer                      │  │   │
│  │  │  • eAushadhi API Client                          │  │   │
│  │  │  • HTTP Request/Response                         │  │   │
│  │  │  • Error Handling & Retry                        │  │   │
│  │  └──────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                             │
                             │ HTTPS
                             ▼
                   ┌─────────────────────┐
                   │  eAushadhi Platform │
                   │  (NHA, India)       │
                   └─────────────────────┘
```

## Workflow

1. **Admin Configuration**
   - Admin logs into CARE
   - Navigates to institute mapping admin
   - Creates facility-to-institute mapping
   - Configures supplier-to-warehouse mappings
   - Sets workflow permissions

2. **Inward Fetch**
   - User creates delivery order in CARE
   - Plugin initiates fetch from eAushadhi API
   - Inward records are fetched and stored
   - Status is tracked via fetch log

3. **Product Mapping**
   - User maps eAushadhi drugs to CARE products
   - Mappings are stored for future use
   - Fuzzy search helps find correct products

4. **Delivery Record Creation**
   - Inward records are linked to delivery orders
   - Items are mapped to delivery items
   - Quantities and batch details are transferred

5. **Approval**
   - User reviews and approves delivery
   - Workflow transitions to CARE native flow
   - Stock is updated in CARE inventory

## Version

**v1.0.0-BETA** - Beta Release (Karnataka-Specific)

This is a beta release and may undergo breaking changes in future versions.

> **Note**: This version is specifically tailored for Karnataka state deployments. Future releases will include a generalized version compatible with eAushadhi deployments across all states in India.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=care_eaushadhi --cov-report=html

# Run specific test
pytest tests/test_models.py::TestInstituteMapping
```

For detailed testing guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:

- Setting up development environment
- Code style and standards
- Writing tests
- Submitting pull requests
- Creating database migrations

## Documentation

- **API Documentation**: [docs/](docs/) - Detailed API endpoint documentation
- **Contributing Guide**: [CONTRIBUTING.md](CONTRIBUTING.md) - Development guidelines
- **Changelog**: [CHANGELOG.md](CHANGELOG.md) - Version history
- **Design Docs**: [eAushadhi Design Documentation](https://care-ecosystem.github.io/Designs/features/eaushadhi-v2/index.html)

## Support

For issues and questions:
- **GitHub Issues**: [https://github.com/ohcnetwork/care_eaushadhi/issues](https://github.com/ohcnetwork/care_eaushadhi/issues)
- **CARE Community**: [care.ohc.network](https://care.ohc.network)
- **Email Support**: [jagan.kumar@egovernments.org](mailto:jagan.kumar@egovernments.org)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [eGov Foundation](https://egov.org.in) - Development and implementation
- CARE Platform Team - Base platform and support
- eAushadhi Team (National Health Authority, India) - API specifications
- Open Healthcare Network - Platform maintenance
- Karnataka State Health Department - Pilot deployment

---

**Note**: This is a beta release (v1.0.0-BETA). Features and APIs may change in future versions. Always refer to the latest documentation for production deployments.

---

This plugin was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) using the [ohcnetwork/care-plugin-cookiecutter](https://github.com/ohcnetwork/care-plugin-cookiecutter).
