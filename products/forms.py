from django import forms

from .models import Category, HtsCode, ImprintMethod, Product, Vendor


def category_choices():
    choices = [("", "— Select Category —")]
    choices += [(c.code, f"{c.code} – {c.description}") for c in Category.objects.all()]
    return choices


def hts_choices():
    choices = [("", "— Select HTS Code —")]
    choices += [(h.pk, f"{h.code} — {h.description}") for h in HtsCode.objects.all()]
    return choices


def vendor_choices():
    choices = [("", "— Select Vendor —")]
    choices += [(v.pk, v.name) for v in Vendor.objects.all()]
    return choices


class CreateProductForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].widget = forms.Select(choices=category_choices())
        self.fields["category"].required = False
        self.fields["hts_code"].widget = forms.Select(choices=hts_choices())
        self.fields["hts_code"].required = False
        self.fields["hts_code"].label = "HTS Code"
        self.fields["vendor_ref"].widget = forms.Select(choices=vendor_choices())
        self.fields["vendor_ref"].required = False
        self.fields["vendor_ref"].label = "Vendor"
        self.fields["vendor"].required = False   # legacy field, not shown in template
        self.fields["vendor_sku"].required = False
        self.fields["production_time"].required = False
        self.fields["estimated_launch"].required = False
        self.fields["imprint_dimension"].required = False
        self.fields["imprint_location"].required = False
        # imprint_method is a legacy field not included in Meta.fields — blank=True on the model is sufficient
        # Render imprint methods as plain checkboxes (styled in the template)
        self.fields["imprint_methods"].queryset = ImprintMethod.objects.all()
        self.fields["imprint_methods"].required = False
        self.fields["imprint_methods"].label = "Imprint Methods"

    class Meta:
        model = Product
        fields = [
            "sku",
            "name",
            "category",
            "hts_code",
            "vendor_ref",
            "image",
            "moq",
            "package",
            "production_time",
            "estimated_launch",
            "description",
            "vendor",
            "vendor_sku",
            "carton_qty",
            "carton_weight",
            "carton_width",
            "carton_length",
            "carton_height",
            "imprint_location",
            "imprint_dimension",
            "imprint_methods",
            "mold_fee",
            "other_imprint",
            "air_freight",
            "ocean_freight",
            "duty_percent",
            "tariff_percent",
            "sourcing",
            "needs_overseas_sku",
            "price_list",
            "npds_done",
            "qb_added",
            "status",
            "colors",
        ]

        widgets = {
            "description": forms.Textarea(attrs={"class": "form-control"}),
            "imprint_methods": forms.CheckboxSelectMultiple(),
            "mold_fee": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "placeholder": "e.g. 250.00"}),
            "other_imprint": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Laser Engraving"}),
        }

        labels = {
            "sku": "SKU",
            "name": "Product Name",
            "category": "Category",
            "image": "Product Image",
            "moq": "MOQ",
            "package": "Package",
            "production_time": "Production Time",
            "estimated_launch": "Estimated Launch",
            "description": "Specifications",
            "vendor": "Vendor",
            "vendor_sku": "Vendor SKU",
            "carton_qty": "Carton Quantity",
            "carton_weight": "Carton Weight",
            "carton_width": "Carton Width",
            "carton_length": "Carton Length",
            "carton_height": "Carton Height",
            "imprint_location": "Imprint Location",
            "imprint_dimension": "Imprint Dimension",
            "imprint_methods": "Imprint Methods",
            "mold_fee": "Mold Fee (setup $)",
            "other_imprint": "Other Imprint Method",
            "air_freight": "Air Freight",
            "ocean_freight": "Ocean Freight",
            "duty_percent": "Duty Percent",
            "tariff_percent": "Tariff Percent",
            "sourcing": "Sourcing",
            "needs_overseas_sku": "Overseas SKU Needed",
            "price_list": "Price List",
            "npds_done": "NPDS Done",
            "qb_added": "QB Added",
            "status": "Status",
            "colors": "Colors",
        }
