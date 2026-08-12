# Product Mapping Data Directory

This directory contains CSV files for bulk importing eAushadhi product mappings.

## Sample File

A sample CSV file is provided: **`sample.csv`**

This file demonstrates the correct format and includes example data. Use it as a template for your imports.

## CSV Format

The import CSV file must contain the following columns:

- **EAushadhi Drug ID**: The drug ID from eAushadhi (required)
- **EAushadhi Drug Name**: The drug name from eAushadhi (required)
- **Product Knowledge Name**: The product name in CARE (for reference only)
- **Product Knowledge Slug**: The slug of the product in CARE (required, without the `f-{facility_id}-` prefix)

### Example (see sample.csv)

```csv
EAushadhi Drug ID,EAushadhi Drug Name,Product Knowledge Name,Product Knowledge Slug
12345,Paracetamol 500mg,Paracetamol,paracetamol-500mg
67890,Amoxicillin 250mg,Amoxicillin,amoxicillin-250mg
11111,Metformin 500mg,Metformin,metformin-500mg
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

## Directory Structure

```
data/
├── sample.csv           # Sample file (tracked in git)
├── prod/                # Production mapping files (gitignored)
│   ├── MysoreDHMapping.csv
│   └── README.md
└── README.md
```

## Notes

- CSV files in this directory are not tracked by git (excluded via .gitignore)
- **Exception**: `sample.csv` is tracked and included in the package distribution
- Production files in `prod/` directory are gitignored for security
- The command will automatically look for files in this directory if a relative path is given
- You can copy `sample.csv` to create your own import file:
  ```bash
  cp sample.csv my_facility_mappings.csv
  # Edit my_facility_mappings.csv with your data
  ```
