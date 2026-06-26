# Product Mapping Bulk Import Script

This script creates product mappings with the mapping type `BULK_IMPORT` by reading data from a CSV file and invoking the required APIs.

## System Requirements

- Python 3.8 or later
- Internet access
- Valid admin credentials

## Project Structure

```text
.
├── product_mapping_import.py
├── sample.csv
└── README.md
```

## Features

- Generates an authentication token using the provided admin credentials.
- Reads product mapping data from a CSV file.
- Creates product mappings with the mapping type `BULK_IMPORT`.
- Continues processing even if one or more CSV rows are invalid, while logging the corresponding errors.

## CSV Format

The input CSV must contain the following columns:

| Column | Description |
|--------|-------------|
| Facility ID | UUID of the facility |
| EAushadhi Drug ID | eAushadhi drug identifier (e.g. `D00185`) |
| EAushadhi Drug Name | Full name of the drug (e.g. `Amoxycillin Capsules IP 250 mg 1x1`) |
| Product Knowledge ID | UUID of the product knowledge entry |

A `sample.csv` is included in this repository:


| Facility ID | EAushadhi Drug ID | EAushadhi Drug Name | Product Knowledge ID |
| ----------- | ----------------- | ------------------- | ------------ |
| e1ff13b6-383a-4217-a367-f421f7bbe478 | D00185 | Amoxycillin Capsules IP 250 mg 1x1 | 0d6e92a1-dda5-4b2f-a8df-8bb71cb136b4 | 


## Configuration

Open `product_mapping_import.py` and update the configuration block at the top:

```python
BASE_URL = "https://your-care-instance.example.com"
USERNAME  = "your-admin-username"
PASSWORD  = "your-admin-password"
CSV_FILE  = "sample.csv"   # path to your input CSV
```

## Running the Script

1. Install the dependency:

    ````bash
    pip install requests
    ````

2. Update the configuration as described above.
3. Place the input CSV file in the project directory.
4. Run the script:

    ```bash
    python product_mapping_import.py
    ```


### NOTE 
If `python` is not recognised, try `python3 product_mapping_import.py`.


## Error Handling

- Invalid CSV rows (missing values) are skipped with a warning.
- HTTP and unexpected errors for individual rows are logged without stopping the run.
- A final summary line reports the total number of successes and errors/skips.
