import csv
import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from care.emr.models import ProductKnowledge
from care.facility.models import Facility
from care_eaushadhi.models.eaushadhi_product_mapping import EAushadhiProductMapping


class Command(BaseCommand):
    help = "Import eAushadhi product mappings from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Path to CSV file containing product mappings",
        )
        parser.add_argument(
            "--facility",
            type=str,
            required=True,
            help="Facility external ID for the mappings",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate CSV without creating mappings",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Number of records to insert per batch (default: 500)",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        facility_id = options["facility"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        # Resolve CSV file path
        csv_path = Path(csv_file)
        if not csv_path.is_absolute():
            # If relative path, try app's data directory first
            data_dir = Path(__file__).parent.parent.parent / "data"
            csv_path = data_dir / csv_file
            if not csv_path.exists():
                # Fall back to current working directory
                csv_path = Path(csv_file).resolve()

        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        # Validate facility
        try:
            facility = Facility.objects.get(external_id=facility_id)
        except Facility.DoesNotExist:
            raise CommandError(f"Facility not found with external_id: {facility_id}")

        self.stdout.write(f"Starting eAushadhi product mapping import...")
        self.stdout.write(f"Facility: {facility.name} ({facility.external_id})")
        self.stdout.write(f"CSV file: {csv_path}")
        self.stdout.write(f"Batch size: {batch_size}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Process CSV
        success_count = 0
        error_count = 0
        duplicate_count = 0
        required_columns = {
            "EAushadhi Drug ID",
            "EAushadhi Drug Name",
            "Product Knowledge Name",
            "Product Knowledge Slug",
        }

        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                # Validate columns
                if not required_columns.issubset(set(reader.fieldnames or [])):
                    missing = required_columns - set(reader.fieldnames or [])
                    raise CommandError(
                        f"CSV file is missing required columns: {', '.join(sorted(missing))}"
                    )

                self.stdout.write("CSV file validated. Validating data...")

                # First pass: Validate all rows and collect data
                rows_to_process = []
                seen_drug_ids = {}  # Track duplicates within CSV
                product_knowledge_slugs_needed = set()

                for line_number, row in enumerate(reader, start=2):
                    drug_id = row.get("EAushadhi Drug ID", "").strip()
                    drug_name = row.get("EAushadhi Drug Name", "").strip()
                    product_knowledge_name = row.get("Product Knowledge Name", "").strip()
                    product_knowledge_slug = row.get("Product Knowledge Slug", "").strip()

                    # Validate required fields
                    if not drug_id or not drug_name or not product_knowledge_slug:
                        missing_fields = []
                        if not drug_id:
                            missing_fields.append("EAushadhi Drug ID")
                        if not drug_name:
                            missing_fields.append("EAushadhi Drug Name")
                        if not product_knowledge_slug:
                            missing_fields.append("Product Knowledge Slug")

                        self.stdout.write(
                            self.style.WARNING(
                                f"Row {line_number} skipped - missing: {', '.join(missing_fields)}"
                            )
                        )
                        error_count += 1
                        continue

                    # Check for duplicate drug_id within CSV
                    if drug_id in seen_drug_ids:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {line_number} error - Duplicate drug ID {drug_id} "
                                f"(already seen at row {seen_drug_ids[drug_id]})"
                            )
                        )
                        error_count += 1
                        continue

                    seen_drug_ids[drug_id] = line_number
                    product_knowledge_slugs_needed.add(product_knowledge_slug)

                    # Store row data for processing
                    rows_to_process.append({
                        "line_number": line_number,
                        "drug_id": drug_id,
                        "drug_name": drug_name,
                        "product_knowledge_slug": product_knowledge_slug,
                    })

                # Stop if there were validation errors
                if error_count > 0:
                    self.stdout.write(
                        self.style.ERROR(
                            f"\nValidation failed with {error_count} error(s). "
                            "Please fix the CSV and try again."
                        )
                    )
                    raise CommandError("CSV validation failed")

                if not rows_to_process:
                    self.stdout.write(self.style.WARNING("No valid rows to process"))
                    return

                self.stdout.write(f"Validated {len(rows_to_process)} rows successfully")

                # Check all product knowledge exists upfront
                self.stdout.write("Checking product knowledge exists...")
                facility_slugs = {
                    f"f-{facility.external_id}-{slug}": slug
                    for slug in product_knowledge_slugs_needed
                }

                existing_pk = ProductKnowledge.objects.filter(
                    slug__in=facility_slugs.keys(),
                    facility=facility,
                    deleted=False,
                ).values_list("slug", flat=True)

                existing_pk_set = set(existing_pk)
                missing_slugs = []

                for facility_slug, original_slug in facility_slugs.items():
                    if facility_slug not in existing_pk_set:
                        missing_slugs.append(original_slug)

                if missing_slugs:
                    self.stdout.write(
                        self.style.ERROR(
                            f"\nProduct knowledge not found for {len(missing_slugs)} slug(s):"
                        )
                    )
                    for slug in sorted(missing_slugs)[:10]:  # Show first 10
                        self.stdout.write(f"  - {slug}")
                    if len(missing_slugs) > 10:
                        self.stdout.write(f"  ... and {len(missing_slugs) - 10} more")
                    raise CommandError("Product knowledge validation failed")

                self.stdout.write(
                    self.style.SUCCESS(
                        f"All {len(product_knowledge_slugs_needed)} product knowledge records found"
                    )
                )

                # Check for existing mappings upfront
                self.stdout.write("Checking for existing mappings...")
                drug_ids = [row["drug_id"] for row in rows_to_process]

                existing_mappings = set(
                    EAushadhiProductMapping.objects.filter(
                        facility=facility,
                        eaushadhi_drug_id__in=drug_ids,
                        mapping_type="BULK_IMPORT",
                    ).values_list("eaushadhi_drug_id", flat=True)
                )

                if existing_mappings:
                    # Find which rows have duplicates
                    duplicate_rows = []
                    for row in rows_to_process:
                        if row["drug_id"] in existing_mappings:
                            duplicate_rows.append(row)

                    self.stdout.write(
                        self.style.WARNING(
                            f"\nFound {len(existing_mappings)} existing BULK_IMPORT mapping(s):"
                        )
                    )
                    for row in duplicate_rows[:10]:  # Show first 10
                        self.stdout.write(
                            f"  Row {row['line_number']}: {row['drug_id']} already mapped"
                        )
                    if len(duplicate_rows) > 10:
                        self.stdout.write(f"  ... and {len(duplicate_rows) - 10} more")

                    # Filter out rows with existing mappings
                    rows_to_process = [
                        row for row in rows_to_process
                        if row["drug_id"] not in existing_mappings
                    ]
                    duplicate_count = len(existing_mappings)

                    if not rows_to_process:
                        self.stdout.write(
                            self.style.WARNING(
                                "\nAll mappings already exist. Nothing to import."
                            )
                        )
                        self.stdout.write("\n" + "=" * 80)
                        self.stdout.write(f"Import complete!")
                        self.stdout.write(f"Successfully created: 0")
                        self.stdout.write(f"Duplicates skipped: {duplicate_count}")
                        self.stdout.write(f"Failed/Skipped: {error_count}")
                        self.stdout.write("=" * 80)
                        return

                    self.stdout.write(
                        f"\n{len(rows_to_process)} new mapping(s) will be created"
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS("No existing mappings found - all rows are new")
                    )

                # Now process the validated rows in batches
                self.stdout.write(f"\nStarting batch import of {len(rows_to_process)} mapping(s)...")

                # Build lookup for product knowledge
                pk_lookup = {
                    pk.slug: pk
                    for pk in ProductKnowledge.objects.filter(
                        slug__in=facility_slugs.keys(),
                        facility=facility,
                        deleted=False,
                    )
                }

                mappings_to_create = []
                row_metadata = []

                for row in rows_to_process:
                    facility_slug = f"f-{facility.external_id}-{row['product_knowledge_slug']}"
                    product_knowledge = pk_lookup[facility_slug]

                    # Prepare mapping object
                    mapping = EAushadhiProductMapping(
                        facility=facility,
                        eaushadhi_drug_id=row["drug_id"],
                        eaushadhi_drug_name=row["drug_name"],
                        product_knowledge=product_knowledge,
                        mapping_type="BULK_IMPORT",
                        usage_count=0,
                        last_used_date=None,
                    )

                    mappings_to_create.append(mapping)
                    row_metadata.append({
                        "line_number": row["line_number"],
                        "drug_id": row["drug_id"],
                        "drug_name": row["drug_name"],
                    })

                    # Process in batches
                    if len(mappings_to_create) >= batch_size:
                        if not dry_run:
                            created = self._bulk_create_mappings(
                                mappings_to_create, row_metadata
                            )
                            success_count += created
                        else:
                            for metadata in row_metadata:
                                self.stdout.write(
                                    f"Row {metadata['line_number']}: Would create mapping for {metadata['drug_id']}"
                                )
                            success_count += len(mappings_to_create)

                        mappings_to_create = []
                        row_metadata = []

                # Process remaining mappings
                if mappings_to_create:
                    if not dry_run:
                        created = self._bulk_create_mappings(
                            mappings_to_create, row_metadata
                        )
                        success_count += created
                    else:
                        for metadata in row_metadata:
                            self.stdout.write(
                                f"Row {metadata['line_number']}: Would create mapping for {metadata['drug_id']}"
                            )
                        success_count += len(mappings_to_create)

        except FileNotFoundError:
            raise CommandError(f"CSV file not found: {csv_path}")
        except Exception as e:
            raise CommandError(f"Error processing CSV: {e}")

        # Summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(f"Import complete!")
        self.stdout.write(f"Successfully created: {success_count}")
        self.stdout.write(f"Duplicates skipped: {duplicate_count}")
        self.stdout.write(f"Failed/Skipped: {error_count}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes were made"))
        self.stdout.write("=" * 80)

        if error_count > 0:
            sys.exit(1)

    def _bulk_create_mappings(self, mappings, metadata):
        """
        Bulk create mappings. All validation has been done upfront.
        Returns created_count
        """
        created_count = 0
        try:
            with transaction.atomic():
                created_mappings = EAushadhiProductMapping.objects.bulk_create(
                    mappings,
                    batch_size=500,
                )
                created_count = len(created_mappings)

                # Report success for created mappings
                for i, mapping in enumerate(mappings):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Row {metadata[i]['line_number']}: "
                            f"Mapping created for {metadata[i]['drug_id']}"
                        )
                    )
        except IntegrityError as e:
            # This shouldn't happen since we validated upfront,
            # but handle race conditions gracefully
            self.stdout.write(
                self.style.ERROR(
                    f"Batch insert failed (possible race condition): {e}\n"
                    "Falling back to individual inserts for this batch..."
                )
            )
            # Fall back to individual inserts for this batch
            for i, mapping in enumerate(mappings):
                try:
                    mapping.save()
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Row {metadata[i]['line_number']}: "
                            f"Mapping created for {metadata[i]['drug_id']}"
                        )
                    )
                except IntegrityError as inner_e:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Row {metadata[i]['line_number']} skipped - "
                            f"Integrity error: {inner_e}"
                        )
                    )

        return created_count
