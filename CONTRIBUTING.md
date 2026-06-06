# Contributing to eAushadhi Backend Plugin

Thank you for your interest in contributing to the eAushadhi Backend Plugin for CARE! This document provides guidelines and instructions for contributing to this Django-based backend plugin.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)
- [Documentation](#documentation)
- [Database Migrations](#database-migrations)

## Code of Conduct

This project follows the CARE Community Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/care_eaushadhi.git
   cd care_eaushadhi
   ```
3. **Add the upstream repository**:
   ```bash
   git remote add upstream https://github.com/ohcnetwork/care_eaushadhi.git
   ```

## Development Setup

### Prerequisites

- Python 3.10 or higher
- CARE backend repository cloned locally
- Docker and Docker Compose (for development environment)
- Git
- PostgreSQL (via Docker)
- Redis (via Docker)

### Setup for Local Development

#### Option 1: Development with CARE Backend (Recommended)

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
       configs={
           # Add any configuration here
       },
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

7. **Access the development environment**:
   - Backend: `http://localhost:9000`
   - API Docs: `http://localhost:9000/swagger/`

#### Option 2: Standalone Development

1. **Create a virtual environment**:
   ```bash
   cd care_eaushadhi
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -e .
   pip install -r requirements-dev.txt  # If available
   ```

3. **Install CARE as dependency** (for testing):
   ```bash
   pip install -e /path/to/care
   ```

### Verifying Installation

```bash
# Inside CARE backend
docker-compose exec backend python manage.py shell

# Run this in the shell
>>> from django.conf import settings
>>> print('care_eaushadhi' in settings.INSTALLED_APPS)
True

>>> from care_eaushadhi.models import EAushadhiInstituteMapping
>>> print("Plugin installed successfully!")
```

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title and description**
- **Python/Django version**
- **CARE backend version**
- **Steps to reproduce** the issue
- **Expected behavior**
- **Actual behavior**
- **Error messages and stack traces**
- **Environment details** (OS, Docker version)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Clear title and description**
- **Detailed explanation** of the proposed functionality
- **Use cases** and benefits
- **API design examples** (if applicable)
- **Database schema changes** (if applicable)

### Code Contributions

1. **Pick an issue** or create a new one discussing your proposed changes
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes** following the coding standards
4. **Write tests** for your changes
5. **Run tests** to ensure nothing is broken
6. **Update documentation** if needed
7. **Commit your changes** with clear commit messages
8. **Push to your fork**:
   ```bash
   git push origin feature/amazing-feature
   ```
9. **Create a Pull Request** on GitHub

## Coding Standards

### Python/Django Guidelines

- **Python Version**: Support Python 3.10+
- **Django Version**: Follow CARE's Django version requirements (4.2+)
- **Code Style**: Follow PEP 8 with Black formatter
- **Type Hints**: Use type hints for function signatures
- **Docstrings**: Use Google-style docstrings for classes and functions

### Code Style

#### Formatting

- Use **Black** for code formatting:
  ```bash
  black src/care_eaushadhi/
  ```

- Use **isort** for import sorting:
  ```bash
  isort src/care_eaushadhi/
  ```

- Use **flake8** for linting:
  ```bash
  flake8 src/care_eaushadhi/
  ```

#### Naming Conventions

- **Models**: PascalCase (e.g., `EAushadhiInstituteMapping`)
- **Functions/Methods**: snake_case (e.g., `get_institute_mapping`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_SCHEMA_VERSION`)
- **Private methods**: Prefix with underscore (e.g., `_internal_method`)

### Django Best Practices

#### Models

```python
from care.emr.models.base import EMRBaseModel
from django.db import models

class EAushadhiProductMapping(EMRBaseModel):
    """
    Maps eAushadhi drug IDs to CARE product knowledge base.

    Attributes:
        drug_id: eAushadhi drug identifier
        product: Reference to CARE product
        meta: Additional metadata (JSONField)
    """

    drug_id = models.CharField(
        max_length=255,
        help_text="eAushadhi drug identifier"
    )

    product = models.ForeignKey(
        "emr.Product",
        on_delete=models.CASCADE,
        related_name="eaushadhi_mappings",
        help_text="CARE product reference"
    )

    class Meta:
        db_table = "care_eaushadhi_product_mapping"
        unique_together = [["drug_id", "product"]]
        ordering = ["-created_date"]
        indexes = [
            models.Index(fields=["drug_id"]),
        ]
```

#### ViewSets

```python
from care.emr.api.viewsets.base import EMRBaseViewSet, EMRRetrieveMixin
from rest_framework.decorators import action
from rest_framework.response import Response

class ProductMappingViewSet(EMRRetrieveMixin, EMRBaseViewSet):
    """
    ViewSet for eAushadhi product mappings.

    Endpoints:
    - GET /api/care_eaushadhi/product-mappings/
    - GET /api/care_eaushadhi/product-mappings/{id}/
    - POST /api/care_eaushadhi/product-mappings/search-by-drug/
    """

    queryset = EAushadhiProductMapping.objects.all()
    lookup_field = "external_id"

    @action(detail=False, methods=["post"])
    def search_by_drug(self, request):
        """Search product mappings by eAushadhi drug ID."""
        drug_id = request.data.get("drug_id")
        # Implementation
        return Response({"results": []})
```

#### Specs (Pydantic Models)

```python
from pydantic import UUID4, field_validator
from care.emr.resources.base import EMRResource

class ProductMappingCreateSpec(EMRResource):
    """Input specification for creating product mappings."""

    __model__ = EAushadhiProductMapping
    __exclude__ = ["id", "created_by", "updated_by", "created_date"]

    drug_id: str
    product_id: UUID4
    meta: dict | None = None

    @field_validator("drug_id")
    @classmethod
    def validate_drug_id(cls, v):
        """Validate drug ID format."""
        if not v or len(v) < 3:
            raise ValueError("Drug ID must be at least 3 characters")
        return v.strip()
```

### File Organization

```
src/care_eaushadhi/
├── __init__.py
├── apps.py                          # Django app configuration
├── settings.py                      # Plugin settings
├── urls.py                          # URL routing
├── admin.py                         # Django admin registration
├── models/                          # Database models
│   ├── __init__.py
│   ├── eaushadhi_institute_mapping.py
│   ├── eaushadhi_product_mapping.py
│   └── eaushadhi_delivery_record.py
├── api/
│   ├── specs/                       # Pydantic models
│   │   ├── __init__.py
│   │   ├── institute_mapping.py
│   │   └── product_mapping.py
│   └── viewsets/                    # DRF ViewSets
│       ├── __init__.py
│       ├── institute_mapping.py
│       └── product_mapping.py
├── tasks/                           # Celery tasks (if needed)
│   ├── __init__.py
│   └── sync_tasks.py
├── utils/                           # Utility functions
│   ├── __init__.py
│   └── api_client.py
└── migrations/                      # Database migrations
    ├── __init__.py
    └── 0001_initial.py
```

### Security Considerations

- **Never commit secrets** or API keys
- **Use environment variables** for sensitive configuration
- **Validate all user input** in specs and serializers
- **Use parameterized queries** (Django ORM does this automatically)
- **Implement proper permissions** on all ViewSets
- **Sanitize external API data** before storing

## Commit Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks
- **perf**: Performance improvements
- **ci**: CI/CD changes

### Scopes

- **mapping**: Institute/product mapping related
- **api**: API endpoints
- **models**: Database models
- **specs**: Pydantic specifications
- **migrations**: Database migrations
- **tasks**: Celery tasks
- **admin**: Django admin

### Examples

```bash
feat(mapping): add bulk product mapping endpoint

Implement POST /product-mappings/bulk/ endpoint to create
multiple product mappings in a single request.

Closes #45
```

```bash
fix(api): resolve institute mapping search issue

Fixed issue where institute mapping search was not filtering
by facility correctly. Added proper Q object filtering.

Fixes #78
```

```bash
docs(api): add OpenAPI specs for delivery endpoints

Added comprehensive OpenAPI documentation for all delivery
record endpoints with request/response examples.
```

## Pull Request Process

1. **Update documentation** if you're changing functionality
2. **Add tests** for new features (aim for 80%+ coverage)
3. **Ensure all tests pass**:
   ```bash
   pytest
   ```
4. **Run linters and formatters**:
   ```bash
   black src/care_eaushadhi/
   isort src/care_eaushadhi/
   flake8 src/care_eaushadhi/
   ```
5. **Update CHANGELOG.md** with your changes
6. **Create database migrations** if models changed:
   ```bash
   python manage.py makemigrations care_eaushadhi
   ```
7. **Request review** from maintainers
8. **Address review comments** promptly
9. **Squash commits** if requested

### PR Title Format

Use the same format as commit messages:
```
feat(component): brief description
```

### PR Description Template

```markdown
## Description
[Describe what this PR does]

## Related Issue
Fixes #[issue number]

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Database migration

## Testing
[Describe how you tested your changes]

### Test Coverage
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Database Changes
- [ ] New migrations created
- [ ] Migrations tested locally
- [ ] Migrations are reversible
- [ ] No data loss in migrations

## Checklist
- [ ] My code follows the project's coding standards
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published
- [ ] I have run Black, isort, and flake8
- [ ] I have updated the CHANGELOG.md
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_models.py

# Run with coverage
pytest --cov=care_eaushadhi --cov-report=html

# Run specific test
pytest tests/test_models.py::TestProductMapping::test_create_mapping
```

### Writing Tests

Use pytest with pytest-django:

```python
import pytest
from django.contrib.auth import get_user_model
from care_eaushadhi.models import EAushadhiProductMapping

User = get_user_model()

@pytest.mark.django_db
class TestProductMapping:
    """Tests for EAushadhiProductMapping model."""

    def test_create_mapping(self, facility, product, user):
        """Test creating a product mapping."""
        mapping = EAushadhiProductMapping.objects.create(
            drug_id="TEST123",
            product=product,
            created_by=user,
            updated_by=user
        )

        assert mapping.drug_id == "TEST123"
        assert mapping.product == product
        assert str(mapping.external_id) is not None

    def test_duplicate_mapping_fails(self, product, user):
        """Test that duplicate drug_id + product fails."""
        EAushadhiProductMapping.objects.create(
            drug_id="TEST123",
            product=product,
            created_by=user,
            updated_by=user
        )

        with pytest.raises(Exception):  # IntegrityError
            EAushadhiProductMapping.objects.create(
                drug_id="TEST123",
                product=product,
                created_by=user,
                updated_by=user
            )
```

### Test Fixtures

Create fixtures in `conftest.py`:

```python
import pytest
from care.facility.models import Facility
from care.emr.models import Product

@pytest.fixture
def facility(user):
    """Create a test facility."""
    return Facility.objects.create(
        name="Test Facility",
        created_by=user
    )

@pytest.fixture
def product(user):
    """Create a test product."""
    return Product.objects.create(
        name="Test Product",
        created_by=user
    )
```

## Documentation

### Code Documentation

- Add **docstrings** for:
  - All models (class-level)
  - All ViewSets and custom actions
  - Complex utility functions
  - All public APIs

```python
def search_product_mappings(drug_id: str, limit: int = 10) -> list[EAushadhiProductMapping]:
    """
    Search for product mappings by eAushadhi drug ID.

    Args:
        drug_id: The eAushadhi drug identifier to search for
        limit: Maximum number of results to return (default: 10)

    Returns:
        List of matching EAushadhiProductMapping instances

    Raises:
        ValueError: If drug_id is empty or invalid

    Examples:
        >>> mappings = search_product_mappings("DRUG123", limit=5)
        >>> len(mappings)
        2
    """
    if not drug_id:
        raise ValueError("drug_id cannot be empty")

    return EAushadhiProductMapping.objects.filter(
        drug_id__icontains=drug_id
    )[:limit]
```

### API Documentation

Create API documentation in `docs/` folder:

```markdown
# Product Mapping API

## Search Product Mappings

**Endpoint**: `POST /api/care_eaushadhi/product-mappings/search-by-drug/`

**Description**: Search for product mappings by eAushadhi drug ID.

**Request**:
```json
{
  "drug_id": "DRUG123",
  "limit": 10
}
```

**Response** (200 OK):
```json
{
  "results": [
    {
      "id": "uuid-here",
      "drug_id": "DRUG123",
      "product": {
        "id": "product-uuid",
        "name": "Paracetamol 500mg"
      }
    }
  ]
}
```
```

### README Updates

Update README.md when you:
- Add new features
- Change setup instructions
- Modify configuration
- Update dependencies

## Database Migrations

### Creating Migrations

```bash
# Navigate to CARE backend root
cd /path/to/care

# Create migrations for the plugin
python manage.py makemigrations care_eaushadhi

# Review the generated migration
cat care_eaushadhi/migrations/0002_auto_*.py

# Apply migrations
python manage.py migrate care_eaushadhi

# Check migration status
python manage.py showmigrations care_eaushadhi
```

### Migration Best Practices

1. **Always review** generated migrations before committing
2. **Test migrations** both forward and backward:
   ```bash
   # Forward
   python manage.py migrate care_eaushadhi

   # Backward (to previous migration)
   python manage.py migrate care_eaushadhi 0001
   ```
3. **Avoid data loss** - use `RunPython` for data migrations
4. **Keep migrations atomic** - one logical change per migration
5. **Add migration comments** for complex operations

### Example Data Migration

```python
from django.db import migrations

def migrate_old_data(apps, schema_editor):
    """Migrate old product mappings to new schema."""
    ProductMapping = apps.get_model('care_eaushadhi', 'EAushadhiProductMapping')

    for mapping in ProductMapping.objects.all():
        # Update logic here
        mapping.meta = {"migrated": True}
        mapping.save()

def reverse_migration(apps, schema_editor):
    """Reverse the data migration."""
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('care_eaushadhi', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_old_data, reverse_migration),
    ]
```

## Questions?

If you have questions:
- Check existing [documentation](docs/)
- Search [existing issues](https://github.com/ohcnetwork/care_eaushadhi/issues)
- Ask in CARE Community forums
- Create a new issue with the `question` label

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to the eAushadhi Backend Plugin! 🎉
