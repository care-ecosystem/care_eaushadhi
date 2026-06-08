from django.contrib import admin
from django.utils.html import format_html

from care_eaushadhi.models import (
    EAushadhiInstituteMapping,
    EAushadhiInstituteSupplierMapping,
    EAushadhiProductMapping,
    EAushadhiInwardRecord,
    EAushadhiInwardRecordItem,
    EAushadhiFetchLog,
    EAushadhiInwardRecordDelivery,
    EAushadhiInwardRecordItemDelivery,
)


class InstituteSupplierMappingInline(admin.TabularInline):
    """Inline admin for supplier mappings within institute mapping."""
    model = EAushadhiInstituteSupplierMapping
    extra = 0
    fields = ['supplier', 'eaushadhi_warehouse_name', 'is_default']
    readonly_fields = ['external_id', 'created_date', 'modified_date']
    raw_id_fields = ['supplier']


@admin.register(EAushadhiInstituteMapping)
class EAushadhiInstituteMappingAdmin(admin.ModelAdmin):
    """Admin interface for eAushadhi Institute Mappings."""

    list_display = [
        'facility',
        'eaushadhi_institute_id',
        'schema_version',
        'has_credentials',
        'supplier_count',
        'created_date',
    ]
    list_filter = ['schema_version', 'created_date']
    search_fields = [
        'facility__name',
        'eaushadhi_institute_id',
        'credentials_ref',
    ]
    readonly_fields = [
        'external_id',
        'created_date',
        'modified_date',
        'created_by',
        'updated_by',
        'meta_display',
    ]
    raw_id_fields = ['facility']
    inlines = [InstituteSupplierMappingInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('facility', 'eaushadhi_institute_id', 'schema_version')
        }),
        ('Credentials', {
            'fields': ('credentials_ref',)
        }),
        ('Metadata', {
            'fields': ('meta', 'meta_display'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('external_id', 'created_by', 'updated_by', 'created_date', 'modified_date'),
            'classes': ('collapse',)
        }),
    )

    def has_credentials(self, obj):
        """Display whether credentials are configured."""
        if obj.credentials_ref:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    has_credentials.short_description = 'Has Credentials'

    def supplier_count(self, obj):
        """Display count of supplier mappings."""
        count = obj.supplier_mappings.count()
        return f"{count} supplier(s)"
    supplier_count.short_description = 'Suppliers'

    def meta_display(self, obj):
        """Display meta field in a readable format."""
        if obj.meta:
            return format_html('<pre>{}</pre>', str(obj.meta))
        return '-'
    meta_display.short_description = 'Meta (JSON)'


@admin.register(EAushadhiInstituteSupplierMapping)
class EAushadhiInstituteSupplierMappingAdmin(admin.ModelAdmin):
    """Admin interface for Institute Supplier Mappings."""

    list_display = [
        'institute_mapping',
        'supplier',
        'eaushadhi_warehouse_name',
        'is_default',
        'created_date',
    ]
    list_filter = ['is_default', 'created_date']
    search_fields = [
        'institute_mapping__facility__name',
        'supplier__name',
        'eaushadhi_warehouse_name',
    ]
    readonly_fields = [
        'external_id',
        'created_date',
        'modified_date',
        'created_by',
        'updated_by',
    ]
    raw_id_fields = ['institute_mapping', 'supplier']

    fieldsets = (
        ('Mapping Information', {
            'fields': ('institute_mapping', 'supplier', 'eaushadhi_warehouse_name', 'is_default')
        }),
        ('Audit Information', {
            'fields': ('external_id', 'created_by', 'updated_by', 'created_date', 'modified_date'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EAushadhiProductMapping)
class EAushadhiProductMappingAdmin(admin.ModelAdmin):
    """Admin interface for Product Mappings."""

    list_display = [
        'eaushadhi_drug_id',
        'eaushadhi_drug_name',
        'product_knowledge',
        'facility',
        'usage_count',
        'last_used_date',
    ]
    list_filter = ['facility', 'last_used_date', 'created_date']
    search_fields = [
        'eaushadhi_drug_id',
        'eaushadhi_drug_name',
        'product_knowledge__name',
        'facility__name',
    ]
    readonly_fields = [
        'external_id',
        'usage_count',
        'last_used_date',
        'created_date',
        'modified_date',
        'created_by',
        'updated_by',
    ]
    raw_id_fields = ['facility', 'product_knowledge']

    fieldsets = (
        ('eAushadhi Drug Information', {
            'fields': ('eaushadhi_drug_id', 'eaushadhi_drug_name')
        }),
        ('CARE Product Mapping', {
            'fields': ('facility', 'product_knowledge')
        }),
        ('Usage Statistics', {
            'fields': ('usage_count', 'last_used_date'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('external_id', 'created_by', 'updated_by', 'created_date', 'modified_date'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EAushadhiFetchLog)
class EAushadhiFetchLogAdmin(admin.ModelAdmin):
    """Admin interface for Fetch Logs - useful for debugging."""

    list_display = [
        'external_id',
        'facility',
        'fetch_status_badge',
        'http_status_code',
        'inward_date',
        'created_date',
    ]
    list_filter = ['fetch_status', 'http_status_code', 'inward_date', 'created_date']
    search_fields = [
        'facility__name',
        'delivery_order__external_id',
        'error_message',
        'error_code',
    ]
    readonly_fields = [
        'external_id',
        'facility',
        'delivery_order',
        'fetch_status',
        'http_status_code',
        'inward_date',
        'error_code',
        'error_message',
        'error_details_display',
        'created_date',
    ]
    raw_id_fields = ['facility', 'delivery_order']

    fieldsets = (
        ('Basic Information', {
            'fields': ('facility', 'delivery_order', 'inward_date')
        }),
        ('Status', {
            'fields': ('fetch_status', 'http_status_code')
        }),
        ('Error Information', {
            'fields': ('error_code', 'error_message', 'error_details_display'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('external_id', 'created_date'),
            'classes': ('collapse',)
        }),
    )

    def fetch_status_badge(self, obj):
        """Display fetch status with color coding."""
        colors = {
            'pending': 'gray',
            'in_progress': 'blue',
            'completed': 'green',
            'failed': 'red',
        }
        color = colors.get(obj.fetch_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.fetch_status.upper()
        )
    fetch_status_badge.short_description = 'Status'

    def error_details_display(self, obj):
        """Display error details in a readable format."""
        if obj.error_details:
            return format_html('<pre>{}</pre>', str(obj.error_details))
        return '-'
    error_details_display.short_description = 'Error Details (JSON)'

    def has_add_permission(self, request):
        """Prevent manual creation of fetch logs."""
        return False


@admin.register(EAushadhiInwardRecord)
class EAushadhiInwardRecordAdmin(admin.ModelAdmin):
    """Admin interface for Inward Records."""

    list_display = [
        'external_id',
        'facility',
        'inward_date',
        'sync_status',
        'items_count',
        'created_date',
    ]
    list_filter = ['sync_status', 'inward_date', 'created_date']
    search_fields = [
        'external_id',
        'facility__name',
        'eaushadhi_warehouse_name',
    ]
    readonly_fields = [
        'external_id',
        'facility',
        'eaushadhi_warehouse_name',
        'inward_date',
        'sync_status',
        'raw_data_display',
        'items_current_count',
        'created_date',
        'modified_date',
    ]
    raw_id_fields = ['facility']

    fieldsets = (
        ('Basic Information', {
            'fields': ('facility', 'eaushadhi_warehouse_name', 'inward_date', 'sync_status')
        }),
        ('Statistics', {
            'fields': ('items_current_count',)
        }),
        ('Raw Data', {
            'fields': ('raw_data_display',),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('external_id', 'created_date', 'modified_date'),
            'classes': ('collapse',)
        }),
    )

    def items_count(self, obj):
        """Display count of inward items."""
        return obj.items_current_count or 0
    items_count.short_description = 'Items'

    def raw_data_display(self, obj):
        """Display raw data in a readable format."""
        if obj.raw_data:
            import json
            try:
                formatted = json.dumps(obj.raw_data, indent=2)
                return format_html('<pre>{}</pre>', formatted)
            except:
                return format_html('<pre>{}</pre>', str(obj.raw_data))
        return '-'
    raw_data_display.short_description = 'Raw Data (JSON)'

    def has_add_permission(self, request):
        """Prevent manual creation of inward records."""
        return False


@admin.register(EAushadhiInwardRecordItem)
class EAushadhiInwardRecordItemAdmin(admin.ModelAdmin):
    """Admin interface for Inward Record Items."""

    list_display = [
        'external_id',
        'inward_record',
        'drug_name',
        'batch_no',
        'expiry_date',
        'quantity',
    ]
    list_filter = ['expiry_date', 'created_date']
    search_fields = [
        'drug_id',
        'drug_name',
        'batch_no',
        'inward_record__facility__name',
    ]
    readonly_fields = [
        'external_id',
        'inward_record',
        'drug_id',
        'drug_name',
        'batch_no',
        'expiry_date',
        'pack_size',
        'pack_qty',
        'unit_qty',
        'created_date',
        'modified_date',
    ]
    raw_id_fields = ['inward_record']

    def quantity(self, obj):
        """Display combined quantity information."""
        return f"{obj.pack_qty} packs × {obj.pack_size} = {obj.unit_qty} units"
    quantity.short_description = 'Quantity'

    def has_add_permission(self, request):
        """Prevent manual creation of inward items."""
        return False


# Register remaining models with basic admin
admin.site.register(EAushadhiInwardRecordDelivery)
admin.site.register(EAushadhiInwardRecordItemDelivery)
