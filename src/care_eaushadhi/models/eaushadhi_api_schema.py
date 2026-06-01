from django.db import models

from care.emr.models.base import EMRBaseModel

class EAushadhiApiSchema(EMRBaseModel):
    schema_version = models.CharField(max_length=50)
    endpoint = models.CharField(max_length=500)
    response_code = models.PositiveIntegerField()
    json_schema = models.JSONField(help_text="Draft JSON Schema")

    class Meta:
        verbose_name_plural = "E-Aushadhi API Schemas"
        constraints = [
            models.UniqueConstraint(
                fields=["schema_version", "endpoint", "response_code"],
                name="uniq_schema_endpoint_response"
            )
        ]

    def __str__(self):
        return f"Schema {self.schema_version} - {self.endpoint}"
