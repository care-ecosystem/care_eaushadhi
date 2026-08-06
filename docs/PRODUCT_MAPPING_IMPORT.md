# Product Mapping Bulk Import

This document describes how to use the Django management command for bulk importing eAushadhi product mappings from CSV files.

## Overview

The `import_product_mappings` management command allows you to import eAushadhi product mappings in bulk from a CSV file. This is useful for:

- Initial setup of a new facility
- Bulk updating product mappings
- Migrating mappings from external systems

## Prerequisites

1. CARE backend with care_eaushadhi plugin installed
2. Facility created in CARE with external_id
3. Product Knowledge items created in CARE for the facility
4. CSV file with product mapping data

## CSV File Format

### Required Columns

The CSV file must contain these columns (order doesn't matter):

| Column Name | Description | Required | Example |
|-------------|-------------|----------|---------|
| EAushadhi Drug ID | Drug ID from eAushadhi platform | Yes | `12345` |
| EAushadhi Drug Name | Drug name from eAushadhi | Yes | `Paracetamol 500mg` |
| Product Knowledge Name | Product name in CARE (reference only) | No | `Paracetamol` |
| Product Knowledge Slug | Slug of product in CARE (without facility prefix) | Yes | `paracetamol-500mg` |

### Example CSV

```csv
EAushadhi Drug ID,EAushadhi Drug Name,Product Knowledge Name,Product Knowledge Slug
12345,Paracetamol 500mg Tab,Paracetamol,paracetamol-500mg
67890,Amoxicillin 250mg Cap,Amoxicillin,amoxicillin-250mg
11111,Metformin 500mg Tab,Metformin,metformin-500mg
```

### Important Notes

1. **Product Knowledge Slug**:
   - Provide ONLY the slug without the facility prefix
   - The command will automatically prepend `f-{facility_id}-` to the slug
   - Example: If slug is `paracetamol-500mg` and facility ID is `abc-123`, the command will look for `f-abc-123-paracetamol-500mg`

2. **Product Knowledge Must Exist**:
   - All products must be created in CARE's Product Knowledge before importing
   - The product must be active (`is_active=True`)
   - The product must belong to the specified facility

3. **Duplicate Handling**:
   - The command enforces database uniqueness constraints
   - Each facility can have only one BULK_IMPORT mapping per eAushadhi drug
   - Duplicate mappings will be skipped with an error message

## Command Usage

### Basic Usage

```bash
python manage.py import_product_mappings <csv_file> --facility <facility_external_id>
```

### Arguments

- `csv_file` (required): Path to CSV file
  - Can be absolute path: `/path/to/file.csv`
  - Can be relative to data directory: `Mappingsheet.csv`
  - Can be relative to current directory: `./data/Mappingsheet.csv`

- `--facility` (required): External ID of the facility
  - Must be a valid facility external_id from CARE
  - Example: `063f7b33-33a5-4228-8bfd-d736f73d3655`

- `--dry-run` (optional): Validate CSV without creating mappings
  - Use this to test your CSV file before actual import
  - No database changes will be made

### Examples

#### Example 1: Import from data directory

```bash
python manage.py import_product_mappings Mappingsheet.csv \
  --facility 063f7b33-33a5-4228-8bfd-d736f73d3655
```

#### Example 2: Import with absolute path

```bash
python manage.py import_product_mappings /home/user/data/products.csv \
  --facility 063f7b33-33a5-4228-8bfd-d736f73d3655
```

#### Example 3: Dry run to validate CSV

```bash
python manage.py import_product_mappings Mappingsheet.csv \
  --facility 063f7b33-33a5-4228-8bfd-d736f73d3655 \
  --dry-run
```

## Output

### Success Output

```
Starting eAushadhi product mapping import...
Facility: Apollo Hospital (063f7b33-33a5-4228-8bfd-d736f73d3655)
CSV file: /app/care_eaushadhi/data/Mappingsheet.csv
CSV file validated. Processing rows...
Row 2: Mapping created successfully (ID: abc-def-123)
Row 3: Mapping created successfully (ID: xyz-789-456)
Row 4: Mapping created successfully (ID: qwe-rty-789)

================================================================================
Import complete!
Successful: 3
Failed/Skipped: 0
================================================================================
```

### Error Output

```
Starting eAushadhi product mapping import...
Facility: Apollo Hospital (063f7b33-33a5-4228-8bfd-d736f73d3655)
CSV file: /app/care_eaushadhi/data/Mappingsheet.csv
CSV file validated. Processing rows...
Row 2: Mapping created successfully (ID: abc-def-123)
Row 3: Product knowledge not found: invalid-slug
Row 4: BULK_IMPORT mapping already exists for this facility and eAushadhi drug
Row 5: Mapping created successfully (ID: xyz-789-456)

================================================================================
Import complete!
Successful: 2
Failed/Skipped: 2
================================================================================
```

## Error Handling

The command handles several types of errors:

### 1. Missing Required Fields

```
Row 5 skipped - missing: EAushadhi Drug ID, Product Knowledge Slug
```

**Solution**: Fill in all required fields in the CSV

### 2. Product Knowledge Not Found

```
Row 10 failed - Product knowledge not found: invalid-product-slug
```

**Possible Causes**:
- Product doesn't exist in CARE
- Product is inactive (`is_active=False`)
- Product doesn't belong to the specified facility
- Slug is incorrect

**Solution**:
- Create the product in CARE first
- Verify the product is active
- Check the slug matches exactly (case-sensitive)

### 3. Duplicate Mapping

```
Row 15 failed - BULK_IMPORT mapping already exists for this facility and eAushadhi drug
```

**Cause**: A BULK_IMPORT mapping already exists for this eAushadhi drug and facility

**Solution**:
- Remove duplicate entries from CSV
- Or delete existing mapping first if you want to recreate it

### 4. CSV Format Errors

```
CSV file is missing required columns: EAushadhi Drug Name
```

**Solution**: Ensure CSV has all required column headers (exact spelling, case-sensitive)

## Best Practices

### 1. Always Run Dry Run First

```bash
python manage.py import_product_mappings data.csv --facility <id> --dry-run
```

This helps catch errors before making any database changes.

### 2. Prepare Product Knowledge First

Before importing:
1. Create all products in CARE's Product Knowledge
2. Verify all products are active
3. Note down the exact slugs

### 3. Test with Small Sample

Test with a small CSV (5-10 rows) before importing hundreds of mappings.

### 4. Review CSV Format

- Use UTF-8 encoding
- Ensure no extra spaces in column names
- Verify data in required columns

### 5. Backup Before Import

Since this creates database records, consider backing up the database before large imports.

## Troubleshooting

### Issue: "Facility not found"

**Error**: `Facility not found with external_id: abc-123`

**Solution**: Verify the facility external_id is correct. You can check in CARE admin or database.

### Issue: "CSV file not found"

**Error**: `CSV file not found: /path/to/file.csv`

**Solutions**:
- Check file path is correct
- Use absolute path
- Place file in `src/care_eaushadhi/data/` and use filename only

### Issue: "Multiple product knowledge found"

**Error**: `Multiple product knowledge found: product-slug`

**Solution**: This indicates data integrity issue. Check database for duplicate slugs for the same facility.

## Migration from Old Script

If you were previously using the standalone `product_mapping_import.py` script:

### Old Way (Deprecated)

```bash
cd design/product_mapping_script
python product_mapping_import.py
```

### New Way (Recommended)

```bash
# From CARE backend root
python manage.py import_product_mappings \
  src/care_eaushadhi/data/Mappingsheet.csv \
  --facility 063f7b33-33a5-4228-8bfd-d736f73d3655
```

### Key Differences

| Aspect | Old Script | New Command |
|--------|-----------|-------------|
| Authentication | HTTP API (username/password) | Direct database access (no auth needed) |
| Configuration | Hardcoded in script | Command-line arguments |
| Integration | Standalone | Part of Django management commands |
| Performance | Slower (HTTP requests) | Faster (direct DB access) |
| Error Handling | Basic | Comprehensive with transactions |
| Maintenance | Separate script | Version controlled with app |

## Deployment

For production deployments, see [CSV File Management in Deployment](./DEPLOYMENT_CSV_MANAGEMENT.md) which covers:
- Docker volume mounts
- Kubernetes ConfigMaps and PersistentVolumes
- S3/object storage integration
- CI/CD pipelines
- Security best practices

## Related Documentation

- [CSV Deployment Guide](./DEPLOYMENT_CSV_MANAGEMENT.md) - How to manage CSV files in production
- [Product Mapping APIs](../README.md#product-mapping-apis)
- [Contributing Guide](../CONTRIBUTING.md)
- [Database Models](../README.md#database-models)

## Support

For issues or questions:
- GitHub Issues: https://github.com/care-ecosystem/care_eaushadhi/issues
- Email: jagan.kumar@egovernments.org
