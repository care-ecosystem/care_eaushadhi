# CSV File Management in Deployment

This document explains how to manage CSV files for the `import_product_mappings` command in production deployments.

## Overview

CSV files are **not committed to version control** (gitignored) because they contain facility-specific operational data. Here's how to handle them in different deployment environments.

## Deployment Approaches

### 1. Docker Volume Mounts (Recommended for Docker/K8s)

Mount a volume containing CSV files into the container.

#### Docker Compose Example

```yaml
# docker-compose.yml
services:
  backend:
    image: care_backend:latest
    volumes:
      # Mount CSV files directory
      - ./eaushadhi_data:/app/eaushadhi_data:ro  # Read-only mount
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings
```

**Usage:**
```bash
# Place CSV files on host
mkdir -p ./eaushadhi_data
cp Mappingsheet.csv ./eaushadhi_data/

# Run command
docker-compose exec backend python manage.py import_product_mappings \
  /app/eaushadhi_data/Mappingsheet.csv \
  --facility 063f7b33-33a5-4228-8bfd-d736f73d3655
```

#### Kubernetes ConfigMap Example

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: eaushadhi-csv-data
  namespace: care-production
data:
  Mappingsheet.csv: |
    EAushadhi Drug ID,EAushadhi Drug Name,Product Knowledge Name,Product Knowledge Slug
    12345,Paracetamol 500mg,Paracetamol,paracetamol-500mg
    # ... more rows
```

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: care-backend
spec:
  template:
    spec:
      containers:
      - name: backend
        image: care:latest
        volumeMounts:
        - name: csv-volume
          mountPath: /app/eaushadhi_data
          readOnly: true
      volumes:
      - name: csv-volume
        configMap:
          name: eaushadhi-csv-data
```

**Usage:**
```bash
# Run via kubectl exec
kubectl exec -it <pod-name> -- python manage.py import_product_mappings \
  /app/eaushadhi_data/Mappingsheet.csv \
  --facility 063f7b33-33a5-4228-8bfd-d736f73d3655
```

**Note:** ConfigMaps have a 1MB size limit. For large CSVs, use PersistentVolumes instead.

#### Kubernetes PersistentVolume (For Large Files)

```yaml
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: eaushadhi-data-pvc
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 1Gi
```

```yaml
# deployment.yaml
spec:
  template:
    spec:
      containers:
      - name: backend
        volumeMounts:
        - name: eaushadhi-data
          mountPath: /app/eaushadhi_data
      volumes:
      - name: eaushadhi-data
        persistentVolumeClaim:
          claimName: eaushadhi-data-pvc
```

**Upload files to PVC:**
```bash
# Copy CSV to pod
kubectl cp Mappingsheet.csv <pod-name>:/app/eaushadhi_data/

# Run import
kubectl exec -it <pod-name> -- python manage.py import_product_mappings \
  /app/eaushadhi_data/Mappingsheet.csv \
  --facility <facility-id>
```

### 2. Object Storage (S3/GCS/Azure Blob)

Store CSV files in cloud object storage and download before import.

#### S3 Example

```bash
#!/bin/bash
# import-from-s3.sh

FACILITY_ID="063f7b33-33a5-4228-8bfd-d736f73d3655"
S3_BUCKET="care-eaushadhi-data"
CSV_FILE="facility-${FACILITY_ID}/Mappingsheet.csv"
LOCAL_PATH="/tmp/import.csv"

# Download from S3
aws s3 cp "s3://${S3_BUCKET}/${CSV_FILE}" "${LOCAL_PATH}"

# Run import
python manage.py import_product_mappings "${LOCAL_PATH}" --facility "${FACILITY_ID}"

# Cleanup
rm "${LOCAL_PATH}"
```

**With boto3 (Python):**
```python
# management/commands/import_from_s3.py
import boto3
import tempfile
from django.core.management import call_command
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Import product mappings from S3"

    def add_arguments(self, parser):
        parser.add_argument("--s3-key", type=str, required=True)
        parser.add_argument("--facility", type=str, required=True)
        parser.add_argument("--bucket", type=str, default="care-eaushadhi-data")

    def handle(self, *args, **options):
        s3 = boto3.client('s3')

        with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False) as tmp:
            s3.download_file(
                options['bucket'],
                options['s3_key'],
                tmp.name
            )

            call_command(
                'import_product_mappings',
                tmp.name,
                facility=options['facility']
            )
```

### 3. Direct Server Upload (Traditional VPS/VM)

For traditional server deployments, upload files directly.

#### Using SCP

```bash
# Upload CSV to server
scp Mappingsheet.csv user@server:/var/www/care/eaushadhi_data/

# SSH into server and run
ssh user@server
cd /var/www/care
source venv/bin/activate
python manage.py import_product_mappings \
  /var/www/care/eaushadhi_data/Mappingsheet.csv \
  --facility 063f7b33-33a5-4228-8bfd-d736f73d3655
```

#### Using SFTP

```bash
sftp user@server
put Mappingsheet.csv /var/www/care/eaushadhi_data/
exit

ssh user@server
cd /var/www/care
python manage.py import_product_mappings \
  /var/www/care/eaushadhi_data/Mappingsheet.csv \
  --facility <facility-id>
```

### 4. Django Admin File Upload (Future Enhancement)

Create a custom Django admin action to upload and import CSV files via web interface.

**Not yet implemented** - This would require:
1. File upload form in Django admin
2. Temporary file storage
3. Background task processing (Celery)
4. Progress tracking

**Example implementation outline:**
```python
# admin.py
from django.contrib import admin
from django.core.management import call_command

@admin.register(ProductMappingImportTask)
class ProductMappingImportAdmin(admin.ModelAdmin):
    def upload_and_import(self, request):
        if request.method == 'POST':
            csv_file = request.FILES['csv_file']
            facility_id = request.POST['facility_id']

            # Save temporarily
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                for chunk in csv_file.chunks():
                    tmp.write(chunk)

                # Queue import task (use Celery in production)
                call_command('import_product_mappings', tmp.name, facility=facility_id)
```

## Recommended Approach by Environment

| Environment | Recommended Method | Why |
|-------------|-------------------|------|
| **Local Development** | Place in `src/care_eaushadhi/data/` | Simple, direct access |
| **Docker Compose** | Volume mount from host | Easy to update files |
| **Kubernetes** | PersistentVolume + kubectl cp | Scalable, persistent |
| **AWS/Cloud** | S3 + download script | Secure, centralized storage |
| **Traditional VPS** | SCP/SFTP upload | Standard server admin practice |

## Security Best Practices

### 1. Access Control

```yaml
# Kubernetes RBAC example
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: csv-uploader
rules:
- apiGroups: [""]
  resources: ["pods/exec"]
  verbs: ["create"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["create", "update"]
```

### 2. File Permissions

```bash
# On server, restrict CSV file access
chmod 600 /var/www/care/eaushadhi_data/*.csv
chown www-data:www-data /var/www/care/eaushadhi_data/*.csv
```

### 3. Encryption

For sensitive data, encrypt CSV files:

```bash
# Encrypt before upload
gpg --symmetric --cipher-algo AES256 Mappingsheet.csv

# Upload encrypted file
scp Mappingsheet.csv.gpg user@server:/secure/

# Decrypt on server
gpg --decrypt Mappingsheet.csv.gpg > /tmp/import.csv
python manage.py import_product_mappings /tmp/import.csv --facility <id>
rm /tmp/import.csv  # Cleanup
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/import-mappings.yml
name: Import Product Mappings

on:
  workflow_dispatch:
    inputs:
      facility_id:
        description: 'Facility External ID'
        required: true
      csv_s3_key:
        description: 'S3 key for CSV file'
        required: true

jobs:
  import:
    runs-on: ubuntu-latest
    steps:
      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_KEY }}
          aws-region: us-east-1

      - name: Download CSV from S3
        run: |
          aws s3 cp "s3://care-eaushadhi-data/${{ inputs.csv_s3_key }}" ./import.csv

      - name: Import to production
        run: |
          kubectl exec -n production deployment/care-backend -- \
            python manage.py import_product_mappings /tmp/import.csv \
            --facility ${{ inputs.facility_id }}
```

## Automated Import Pipeline

For recurring imports, set up an automated pipeline:

```bash
#!/bin/bash
# cron-import.sh - Run daily via cron

FACILITIES=(
  "063f7b33-33a5-4228-8bfd-d736f73d3655"
  "another-facility-id"
)

for FACILITY in "${FACILITIES[@]}"; do
  CSV_PATH="/var/data/facility-${FACILITY}/latest-mappings.csv"

  if [ -f "$CSV_PATH" ]; then
    echo "Importing for facility: $FACILITY"
    python manage.py import_product_mappings "$CSV_PATH" \
      --facility "$FACILITY" \
      >> /var/log/care/import.log 2>&1
  fi
done
```

Add to crontab:
```bash
0 2 * * * /opt/care/scripts/cron-import.sh
```

## Troubleshooting

### Issue: File not found in container

**Problem:** CSV file not accessible inside container

**Solutions:**
```bash
# Check if volume is mounted
docker exec <container> ls -la /app/eaushadhi_data

# Verify mount in docker-compose.yml
docker-compose config | grep volumes -A 5

# For Kubernetes, check PVC
kubectl describe pvc eaushadhi-data-pvc
kubectl exec <pod> -- ls -la /app/eaushadhi_data
```

### Issue: Permission denied

**Problem:** Container can't read CSV file

**Solutions:**
```bash
# On host, set proper permissions
chmod 644 ./eaushadhi_data/*.csv

# For Kubernetes, check pod security context
kubectl get pod <pod> -o yaml | grep securityContext -A 5
```

### Issue: ConfigMap too large

**Problem:** CSV file exceeds 1MB ConfigMap limit

**Solution:** Use PersistentVolume instead (see section above)

## Best Practices Summary

1. **Never commit CSV files to git** (except sample files)
2. **Use read-only mounts** when possible
3. **Validate CSV with --dry-run first**
4. **Keep CSV files in secure locations** with proper access controls
5. **Use object storage (S3)** for centralized management
6. **Automate imports** for recurring needs
7. **Log all imports** for audit trail
8. **Clean up temporary files** after import

## Related Documentation

- [Product Mapping Import Guide](./PRODUCT_MAPPING_IMPORT.md)
- [Data Directory README](../src/care_eaushadhi/data/README.md)
