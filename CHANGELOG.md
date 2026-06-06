# Changelog

All notable changes to the eAushadhi Backend Plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-beta] - 2026-06-06

### Added

#### Database Models
- **Institute Mapping System**
  - `EAushadhiInstituteMapping` - Links CARE facilities to eAushadhi institute IDs
  - `EAushadhiInstituteSupplierMapping` - Maps CARE suppliers to eAushadhi warehouse names
  - Support for default supplier selection
  - Schema version management for API compatibility
  - Encrypted credentials reference storage
  - Workflow control via meta flags:
    - `disable_inward_date` - Lock inward date to today
    - `manual_addition` - Allow manual item addition
    - `allow_deleting_inward_after_fetch` - Control deletion of fetched records
    - `allow_updating_quantity_after_received` - Control quantity editing after receipt

- **Product Mapping System**
  - `EAushadhiProductMapping` - Maps eAushadhi drug IDs to CARE products
  - Unique constraint on drug_id and product combination
  - Support for multiple mappings per drug
  - Meta field for additional mapping metadata

- **Inward Records Management**
  - `EAushadhiInwardRecord` - Stores inward records from eAushadhi API
  - `EAushadhiInwardRecordItem` - Individual items in inward records
  - `EAushadhiInwardRecordDelivery` - Links inward records to CARE delivery orders
  - `EAushadhiInwardRecordItemDelivery` - Links inward items to delivery items
  - Support for batch tracking and expiry dates
  - Pack size and quantity management

- **API Schema Management**
  - `EAushadhiAPISchema` - Version tracking for eAushadhi API schemas
  - Schema validation and compatibility checks

- **Fetch Logging**
  - `EAushadhiFetchLog` - Tracks fetch requests and their status
  - Status tracking (pending, in_progress, completed, failed)
  - Error logging and retry support
  - Timestamp tracking for audit trail

#### API Endpoints

##### Institute Mapping APIs
- `POST /api/care_eaushadhi/institute-mappings/` - Create institute mapping
  - Facility validation
  - Duplicate prevention
  - Supplier validation
  - Atomic creation with supplier mappings
- `GET /api/care_eaushadhi/institute-mappings/` - List institute mappings
  - Filtering by facility, eAushadhi institute ID, schema version
  - Ordering support
  - Pagination
- `GET /api/care_eaushadhi/institute-mappings/{id}/` - Retrieve institute mapping
  - Full details with supplier mappings
  - Audit trail (created_by, updated_by)
- `PATCH /api/care_eaushadhi/institute-mappings/{id}/` - Update institute mapping
  - Partial updates (schema_version, credentials_ref, meta)
  - Immutable fields protection (facility_id, eaushadhi_institute_id)
  - Automatic audit trail

##### Product Mapping APIs
- `POST /api/care_eaushadhi/product-mappings/search/` - Search product mappings by drug ID
  - Drug ID-based search
  - Fuzzy matching support
  - Product details in response
  - Pagination support

##### Inward Fetch APIs
- `POST /api/care_eaushadhi/initiate-inward-fetch/` - Initiate inward fetch from eAushadhi
  - Delivery order validation
  - Institute mapping verification
  - Asynchronous fetch with polling support
  - Status tracking via fetch log
  - Retry mechanism for failed fetches

##### Inward Record APIs
- `GET /api/care_eaushadhi/inward-records/` - List inward records
  - Filtering by delivery order
  - Date range filtering
  - Status filtering
- `GET /api/care_eaushadhi/inward-records/{id}/` - Retrieve inward record details
  - Full item list
  - Delivery order linkage
  - Product mapping status

##### Delivery Record APIs
- `POST /api/care_eaushadhi/record-deliveries/` - Create delivery record
  - Links inward record to CARE delivery order
  - Validation of delivery order and inward record
  - Automatic status updates
- `GET /api/care_eaushadhi/record-deliveries/` - List delivery records
  - Filtering by delivery order and inward record
- `GET /api/care_eaushadhi/record-deliveries/{id}/` - Retrieve delivery record details

##### Record Item Delivery APIs
- `POST /api/care_eaushadhi/record-item-deliveries/` - Create item delivery record
  - Links inward items to delivery items
  - Product mapping validation
  - Quantity validation
  - Batch and expiry tracking

#### Pydantic Specifications

- **Institute Mapping Specs**
  - `InstituteMappingCreateSpec` - Input validation for creation
  - `InstituteMappingUpdateSpec` - Input validation for updates
  - `InstituteMappingListSpec` - List view serialization
  - `InstituteMappingRetrieveSpec` - Detail view serialization
  - Field-level validation
  - Nested supplier mapping specs

- **Product Mapping Specs**
  - `ProductMappingSearchSpec` - Search input validation
  - `ProductMappingResponseSpec` - Search response serialization

- **Supplier Mapping Specs**
  - `InstituteSupplierMappingCreateSpec` - Supplier mapping creation
  - `InstituteSupplierMappingReadSpec` - Supplier mapping serialization
  - Default supplier validation

#### Features

- **eAushadhi API Integration**
  - Polling mechanism for inward record fetching
  - Status tracking (loading, success, failed, no_records)
  - Retry logic with exponential backoff
  - Error handling and logging
  - Date format conversion (DD/MM/YYYY for eAushadhi API)

- **Data Validation**
  - Comprehensive Pydantic validation
  - Foreign key validation
  - Unique constraint enforcement
  - Business logic validation (e.g., at most one default supplier)

- **Audit Trail**
  - Created by / Updated by tracking
  - Timestamp tracking (created_date, modified_date)
  - Soft delete support
  - History tracking via EMRBaseModel

- **Query Optimization**
  - Select related for foreign keys
  - Prefetch related for reverse foreign keys
  - Database indexes on frequently queried fields
  - Efficient pagination

- **Security**
  - Credentials stored as encrypted references
  - Permission-based access control
  - Facility-scoped data access
  - Input sanitization and validation

#### Documentation

- **API Documentation**
  - `docs/INSTITUTE_MAPPING_CREATE_API.md` - Institute mapping creation guide
  - `docs/INSTITUTE_MAPPING_UPDATE_API.md` - Institute mapping update guide
  - OpenAPI/Swagger integration
  - Request/response examples
  - Error code documentation

- **Development Documentation**
  - Comprehensive CONTRIBUTING.md
  - Setup instructions for local development
  - Coding standards and best practices
  - Testing guidelines
  - Migration best practices

### Changed

- Updated from cookiecutter template structure to production-ready structure
- Reorganized code into `api/specs/` and `api/viewsets/` for better separation
- Enhanced error messages for better debugging
- Improved validation messages

### Fixed

- Institute mapping serialization issues (meta field not showing)
- Product mapping search endpoint optimization
- Date format handling for eAushadhi API compatibility

### Configuration

**Environment Variables Added**:
- `EAUSHADHI_API_ENDPOINT` - eAushadhi API endpoint URL (Karnataka-specific)
- `EAUSHADHI_API_SECRET_KEY` - Base64 encoded credentials for authentication
- `EAUSHADHI_API_RETRY_COUNT` - Maximum retry attempts (default: 5)
- `EAUSHADHI_API_TIMEOUT` - Overall request timeout (default: 30s)
- `EAUSHADHI_API_CONNECT_TIMEOUT` - Connection timeout (default: 10s)
- `EAUSHADHI_API_READ_TIMEOUT` - Read timeout (default: 30s)
- `EAUSHADHI_API_VERIFY_SSL` - SSL verification flag (default: True)
- `EAUSHADHI_API_PROXY_HTTP` - HTTP proxy URL (optional)
- `EAUSHADHI_API_PROXY_HTTPS` - HTTPS proxy URL (optional)
- `SIMILARITY_THRESHOLD` - Product mapping similarity threshold (default: 0.2)

All settings support three-tier configuration:
1. PLUGIN_CONFIGS in Django settings (highest priority)
2. Environment variables (medium priority)
3. Default values (lowest priority)

### Dependencies

- Django >= 4.2
- djangorestframework >= 3.14
- pydantic >= 2.0
- django-environ >= 0.10 (for environment variable management)
- requests (for eAushadhi API calls)
- CARE backend (as base platform)

### Technical Stack

- **Framework**: Django 4.2+
- **API**: Django REST Framework
- **Validation**: Pydantic v2
- **Database**: PostgreSQL (via CARE)
- **Base Models**: EMRBaseModel from CARE
- **Testing**: pytest, pytest-django
- **Code Quality**: Black, isort, flake8

### Database Schema

- All models use `care_eaushadhi_*` table prefix to avoid conflicts
- Foreign key relationships to CARE core models:
  - Facility (care.facility.models.Facility)
  - User (users.User)
  - Product (care.emr.models.Product)
  - Organization/Supplier (care.emr.models.Organization)
  - SupplyDelivery (care.emr.models.SupplyDelivery)
  - SupplyDeliveryItem (care.emr.models.SupplyDeliveryItem)
- Indexes on frequently queried fields
- Unique constraints for data integrity

### Migration Notes

- Initial migration: `0001_initial.py`
- All models inherit from EMRBaseModel for audit trail
- Soft delete support enabled
- UUID external_id for API exposure

---

## [0.1.0] - 2026-05-29

### Added
- Initial project structure from cookiecutter template
- Basic Django app configuration
- Setup.py for package distribution

---

## Notes

This is the initial beta release. Features and APIs are subject to change in future versions.

For detailed API documentation, refer to the `docs/` directory.

For migration guides and breaking changes, please refer to the main README.md file.

## Future Roadmap

### Planned for v1.1.0
- Bulk product mapping endpoint
- Enhanced error recovery mechanisms
- Webhook support for real-time updates
- Performance optimizations for large datasets
- Enhanced logging and monitoring

### Planned for v2.0.0
- Multi-state support (generalization beyond Karnataka)
- Advanced analytics and reporting
- Scheduled background syncs
- Support for additional eAushadhi API versions
- GraphQL API support
