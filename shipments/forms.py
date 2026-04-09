from django import forms

from .models import Shipment, ShipmentDocument, ShipmentItem


class ShipmentForm(forms.ModelForm):
    class Meta:
        model = Shipment
        fields = [
            "shipment_number",
            "ags_number",
            "po_numbers",
            "mode",
            "carrier",
            "vessel",
            "tracking_number",
            "etd",
            "eta_port",
            "eta_warehouse",
            "date_delivered",
            "port_of_loading",
            "port_of_arrival",
            "status",
            "total_cartons",
            "total_pieces",
            "total_cbm",
            "total_gw_kg",
            "notes",
        ]
        widgets = {
            "etd": forms.DateInput(attrs={"type": "date"}),
            "eta_port": forms.DateInput(attrs={"type": "date"}),
            "eta_warehouse": forms.DateInput(attrs={"type": "date"}),
            "date_delivered": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "po_numbers": forms.TextInput(
                attrs={"placeholder": "e.g. 81083, 81098, 81251"}
            ),
            "ags_number": forms.TextInput(attrs={"placeholder": "e.g. SE00277382"}),
            "tracking_number": forms.TextInput(
                attrs={"placeholder": "AWB# or container/BL#"}
            ),
            "vessel": forms.TextInput(
                attrs={"placeholder": "e.g. ZIM Jade 3E / Voyage 18E"}
            ),
        }


class ShipmentItemForm(forms.ModelForm):
    class Meta:
        model = ShipmentItem
        fields = [
            "po_number",
            "sku",
            "description",
            "cartons",
            "qty",
            "nw_kg",
            "gw_kg",
            "cbm",
            "dimensions_cm",
        ]
        widgets = {
            "description": forms.TextInput(attrs={"placeholder": "Product description"}),
            "dimensions_cm": forms.TextInput(attrs={"placeholder": "e.g. 34.5×34.5×21.5"}),
        }


ShipmentItemFormSet = forms.inlineformset_factory(
    Shipment,
    ShipmentItem,
    form=ShipmentItemForm,
    extra=3,
    can_delete=True,
)


class ShipmentDocumentForm(forms.ModelForm):
    class Meta:
        model = ShipmentDocument
        fields = ["doc_type", "file"]
