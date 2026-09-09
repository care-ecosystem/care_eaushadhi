# Production Mapping Files

This directory contains production-ready mapping CSV files for specific facilities.

## Files

- **MysoreDHMapping.csv** - Mysore District Hospital product mappings

## Usage

These files are **not tracked in git** to keep sensitive facility data out of version control.

### Import Command

```bash
python manage.py import_product_mappings prod/MysoreDHMapping.csv \
  --facility <mysore-dh-facility-id>
```

### With Dry Run

```bash
python manage.py import_product_mappings prod/MysoreDHMapping.csv \
  --facility <mysore-dh-facility-id> \
  --dry-run
```

## CSV Format

All files must follow the standard format:

```csv
EAushadhi Drug ID,EAushadhi Drug Name,Product Knowledge Name,Product Knowledge Slug
12345,Paracetamol 500mg Tab,Paracetamol 500mg,paracetamol-500mg
```

See `../sample.csv` for a complete example.

## Notes

- Files in this directory are gitignored by default
- Only use this directory for facility-specific production mappings
- Keep a backup of your mapping files outside the repository
