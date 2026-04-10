from django.contrib import admin

from .models import Shipment, ShipmentDocument, ShipmentItem


class ShipmentItemInline(admin.TabularInline):
    model = ShipmentItem
    extra = 0


class ShipmentDocumentInline(admin.TabularInline):
    model = ShipmentDocument
    extra = 0
    readonly_fields = ["uploaded_at"]


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = [
        "shipment_number",
        "ags_number",
        "mode",
        "carrier",
        "status",
        "etd",
        "eta_port",
        "eta_warehouse",
    ]
    list_filter = ["mode", "status", "carrier"]
    search_fields = ["shipment_number", "ags_number", "po_numbers", "carrier", "vessel"]
    inlines = [ShipmentItemInline, ShipmentDocumentInline]
