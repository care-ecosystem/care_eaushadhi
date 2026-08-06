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

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        facility_id = options["facility"]
        dry_run = options["dry_run"]

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
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Process CSV
        success_count = 0
        error_count = 0
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

                self.stdout.write("CSV file validated. Processing rows...")

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

                    # Look up product knowledge
                    try:
                        # Product knowledge slug format: f-{facility_id}-{slug}
                        facility_slug = f"f-{facility.external_id}-{product_knowledge_slug}"
                        product_knowledge = ProductKnowledge.objects.get(
                            slug=facility_slug,
                            facility=facility,
                            is_active=True,
                        )
                    except ProductKnowledge.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {line_number} failed - Product knowledge not found: {product_knowledge_slug}"
                            )
                        )
                        error_count += 1
                        continue
                    except ProductKnowledge.MultipleObjectsReturned:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {line_number} failed - Multiple product knowledge found: {product_knowledge_slug}"
                            )
                        )
                        error_count += 1
                        continue

                    # Create mapping
                    if not dry_run:
                        try:
                            with transaction.atomic():
                                mapping = EAushadhiProductMapping.objects.create(
                                    facility=facility,
                                    eaushadhi_drug_id=drug_id,
                                    eaushadhi_drug_name=drug_name,
                                    product_knowledge=product_knowledge,
                                    mapping_type="BULK_IMPORT",
                                    usage_count=0,
                                    last_used_date=None,
                                )
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"Row {line_number}: Mapping created (ID: {mapping.external_id})"
                                    )
                                )
                                success_count += 1
                        except IntegrityError as e:
                            if "uniq_facility_drug_bulk_import" in str(e):
                                msg = "BULK_IMPORT mapping already exists for this facility and eAushadhi drug"
                            else:
                                msg = f"Integrity error: {e}"
                            self.stdout.write(
                                self.style.ERROR(f"Row {line_number} failed - {msg}")
                            )
                            error_count += 1
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Row {line_number} failed - Unexpected error: {e}"
                                )
                            )
                            error_count += 1
                    else:
                        # In dry run mode, just validate
                        self.stdout.write(
                            f"Row {line_number}: Would create mapping for {drug_id} -> {product_knowledge.name}"
                        )
                        success_count += 1

        except FileNotFoundError:
            raise CommandError(f"CSV file not found: {csv_path}")
        except Exception as e:
            raise CommandError(f"Error processing CSV: {e}")

        # Summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(f"Import complete!")
        self.stdout.write(f"Successful: {success_count}")
        self.stdout.write(f"Failed/Skipped: {error_count}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes were made"))
        self.stdout.write("=" * 80)

        if error_count > 0:
            sys.exit(1)
