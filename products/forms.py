from django import forms

from .models import Category, HtsCode, Product, Vendor


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
            "imprint_method",
            "imprint_dimension",
            "air_freight",
            "ocean_freight",
            "duty_percent",
            "tariff_percent",
            "price_list",
            "product_list",
            "hts_list",
            "npds_done",
            "qb_added",
            "published",
            "status",
            "colors",
        ]

        widgets = {
            "description": forms.Textarea(attrs={"class": "form-control"}),
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
            "imprint_method": "Imprint Method",
            "imprint_dimension": "Imprint Dimension",
            "air_freight": "Air Freight",
            "ocean_freight": "Ocean Freight",
            "duty_percent": "Duty Percent",
            "tariff_percent": "Tariff Percent",
            "price_list": "Price List",
            "product_list": "Product List",
            "hts_list": "Added to HTS",
            "npds_done": "NPDS Done",
            "qb_added": "QB Added",
            "published": "Published",
            "status": "Status",
            "colors": "Colors",
        }
