from decimal import Decimal, InvalidOperation

from django import forms

from .models import Shipment, ShipmentDocument, ShipmentItem


class RoundedDecimalField(forms.DecimalField):
    """A DecimalField that rounds to `decimal_places` instead of erroring.

    Packing lists routinely carry more precision than our columns hold
    (e.g. 3.0000 kg into a decimal_places=2 field). Django's default
    behaviour is a hard validation error, which — combined with a form
    that had no error display — looked to the user like "save does nothing".
    Rounding is the right call here: the extra digits are noise.
    """

    def to_python(self, value):
        value = super().to_python(value)
        if value is None or self.decimal_places is None:
            return value
        try:
            return value.quantize(Decimal(1).scaleb(-self.decimal_places))
        except (InvalidOperation, AttributeError):
            return value


class RoundingModelForm(forms.ModelForm):
    """Swaps every DecimalField on the form for a rounding version."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field, forms.DecimalField) and not isinstance(
                field, RoundedDecimalField
            ):
                self.fields[name] = RoundedDecimalField(
                    max_digits=field.max_digits,
                    decimal_places=field.decimal_places,
                    required=field.required,
                    label=field.label,
                    help_text=field.help_text,
                    widget=field.widget,
                    initial=field.initial,
                )


class ShipmentForm(RoundingModelForm):
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
            "total_nw_kg",
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


class ShipmentItemForm(RoundingModelForm):
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
            "unit_cost_usd",
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
