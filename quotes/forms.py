from django import forms

from products.models import Category
from .models import Quote


def category_choices():
    choices = [("", "— Select Category —")]
    choices += [(c.code, f"{c.code} – {c.description}") for c in Category.objects.all()]
    return choices


class CreateQuoteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].widget = forms.Select(choices=category_choices())
        self.fields["category"].required = False

    class Meta:
        model = Quote
        fields = [
            "quote_num",
            "name",
            "vendor",
            "vendor_part_number",
            "category",
            "image",
            "moq",
            "package",
            "production_time",
            "description",
            "air_freight",
            "ocean_freight",
            "duty_percent",
            "tariff_percent",
            "imprint_cost",
            "customer_name",
            "sales_rep",
            "carton_qty",
            "carton_weight",
            "carton_width",
            "carton_length",
            "carton_height",
            "imprint_location",
            "imprint_method",
            "imprint_dimension",
            "quantity1",
            "quantity2",
            "quantity3",
            "quantity4",
            "quantity5",
            "qty1_cost",
            "qty2_cost",
            "qty3_cost",
            "qty4_cost",
            "qty5_cost",
            "qty1_price_air",
            "qty2_price_air",
            "qty3_price_air",
            "qty4_price_air",
            "qty5_price_air",
            "qty1_price_ocean",
            "qty2_price_ocean",
            "qty3_price_ocean",
            "qty4_price_ocean",
            "qty5_price_ocean",
            "status",
            "air_transit_time",
            "ocean_transit_time",
            "notes",
            "reciprocal_tariffs",
        ]
        widgets = {
            "air_freight": forms.TextInput(attrs={"class": "form-control"}),
            "ocean_freight": forms.TextInput(attrs={"class": "form-control"}),
            "air_transit_time": forms.TextInput(attrs={"class": "form-control"}),
            "ocean_transit_time": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.TextInput(attrs={"class": "form-control"}),
            "reciprocal_tariffs": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control"}),
            "quote_num": forms.TextInput(
                attrs={"readonly": "readonly", "class": "form-control"}
            ),
            'status': forms.Select(choices=Quote.STATUS_CHOICES, attrs={'class': 'form-control'}),
        }

        labels = {
            "quote_num": "Quote Number",
            "name": "Product Name",
            "vendor": "Vendor Name",
            "vendor_part_number": "Vendor Part Number",
            "category": "Product Category",
            "image": "Product Image",
            "moq": "Minimum Order Quantity (MOQ)",
            "package": "Package Type",
            "production_time": "Production Time",
            "description": "Product Description",
            "duty_percent": "Duty Percentage",
            "tariff_percent": "Tariff Percentage",
            "imprint_cost": "Imprint Cost",
            "customer_name": "Customer Name",
            "sales_rep": "Sales Representative",
            "carton_qty": "Carton Quantity",
            "carton_weight": "Carton Weight (kg)",
            "carton_width": "Carton Width (cm)",
            "carton_length": "Carton Length (cm)",
            "carton_height": "Carton Height (cm)",
            "imprint_location": "Imprint Location",
            "imprint_method": "Imprint Method",
            "imprint_dimension": "Imprint Dimension (cm)",
            "quantity1": "Quantity Level 1",
            "quantity2": "Quantity Level 2",
            "quantity3": "Quantity Level 3",
            "quantity4": "Quantity Level 4",
            "quantity5": "Quantity Level 5",
            "qty1_cost": "Cost for Quantity 1",
            "qty2_cost": "Cost for Quantity 2",
            "qty3_cost": "Cost for Quantity 3",
            "qty4_cost": "Cost for Quantity 4",
            "qty5_cost": "Cost for Quantity 5",
            "qty1_price_air": "Price Air for Quantity 1",
            "qty2_price_air": "Price Air for Quantity 2",
            "qty3_price_air": "Price Air for Quantity 3",
            "qty4_price_air": "Price Air for Quantity 4",
            "qty5_price_air": "Price Air for Quantity 5",
            "qty1_price_ocean": "Price Ocean for Quantity 1",
            "qty2_price_ocean": "Price Ocean for Quantity 2",
            "qty3_price_ocean": "Price Ocean for Quantity 3",
            "qty4_price_ocean": "Price Ocean for Quantity 4",
            "qty5_price_ocean": "Price Ocean for Quantity 5",
            "status": "Status",
            "air_transit_time": "Air Transit Time",
            "ocean_transit_time": "Ocean Transit Time",
        }


    def clean(self):
        cleaned_data = super().clean()

        # Only perform validation if price fields are present in the data
        if 'qty1_price_air' in self.data or 'qty1_price_ocean' in self.data:
            price_air_q1 = cleaned_data.get("qty1_price_air")
            price_ocean_q1 = cleaned_data.get("qty1_price_ocean")

            # Check if both Q1 price fields are empty or None (or effectively zero)
            is_air_q1_missing = price_air_q1 is None or float(price_air_q1) == 0.0
            is_ocean_q1_missing = price_ocean_q1 is None or float(price_ocean_q1) == 0.0

            if is_air_q1_missing and is_ocean_q1_missing:
                raise forms.ValidationError(
                    "At least one price (Air or Ocean) must be provided for Quantity Level 1."
                )

        # No validation needed for Q2-Q5 as per requirements

        return cleaned_data
