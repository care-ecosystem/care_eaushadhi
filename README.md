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


## Configuration

Open `product_mapping_import.py` and update the configuration block at the top:

```python
BASE_URL = "https://your-care-instance.example.com"
USERNAME  = "your-admin-username"
PASSWORD  = "your-admin-password"
CSV_FILE  = "sample.csv"   # path to your input CSV
```

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


### Steps to get Facility ID from UI
1. Log into CARE using your credentials (username and password).
2. From the home page, click on the facility you want to configure product mapping for.
3. The URL will look like: `.../facility/e1ff13b6-383a-4217-a367-f421f7bbe478/overview`
4. Copy the text between `facility/` and `/overview`, i.e. `e1ff13b6-383a-4217-a367-f421f7bbe478`.
5. Place it in the CSV file in the `Facility ID` column.

### Steps to retrieve Product Knowledge Slug from UI
1. Log into CARE using your credentials (username and password).
2. From the home page, click on the facility you want to configure product mapping for.
3. Expand the sidebar on left hand side if not expanded and expand the `Settings` option.
4. Inside the `Settings` option, click on the `Product Knowledge` option.
5. Click on the category the product exists inside.
6. Using the search bar, search for the product for which you want to create the product mapping.
7. Click on the "View" button.
8. The URL will look like: `.../settings/product_knowledge/f-e1ff13b6-383a-4217-a367-f421f7bbe478-telmisartan-40mg`
9. Copy the text after `product_knowledge/`, i.e. `f-e1ff13b6-383a-4217-a367-f421f7bbe478-telmisartan-40mg`.
10. Paste it in the CSV file in the `Product Knowledge Slug` column.

### Note 
You can also use `care_import_fe` plugin to download a CSV for Product Knowledge information for your facility. From there, you can extract product knowledge slugs.


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
