# Product Mapping Data Directory

This directory contains CSV files for bulk importing eAushadhi product mappings.

## CSV Format

The import CSV file must contain the following columns:

- **EAushadhi Drug ID**: The drug ID from eAushadhi (required)
- **EAushadhi Drug Name**: The drug name from eAushadhi (required)
- **Product Knowledge Name**: The product name in CARE (for reference only)
- **Product Knowledge Slug**: The slug of the product in CARE (required, without the `f-{facility_id}-` prefix)

### Example CSV

```csv
EAushadhi Drug ID,EAushadhi Drug Name,Product Knowledge Name,Product Knowledge Slug
12345,Paracetamol 500mg,Paracetamol,paracetamol-500mg
67890,Amoxicillin 250mg,Amoxicillin,amoxicillin-250mg
```

## Usage

Place your CSV file in this directory and run the management command:

```bash
python manage.py import_product_mappings Mappingsheet.csv --facility <facility-external-id>
```

Or use an absolute path:

```bash
python manage.py import_product_mappings /path/to/your/file.csv --facility <facility-external-id>
```

## Notes

- CSV files in this directory are not tracked by git (excluded via .gitignore)
- Sample CSV files are provided for reference
- The command will automatically look for files in this directory if a relative path is given
