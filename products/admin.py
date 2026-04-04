from django.contrib import admin

from .models import Product, Vendor

# Register your models here.
# admin.site.register(Product)


class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "name",
        "category",
        "price_list",
        "product_list",
        "hts_list",
        "npds_done",
        "qb_added",
        "published",
    )
    list_filter = ("category",)
    search_fields = ("name", "category", "sku")


# register the site with custom admin
admin.site.register(Product, ProductAdmin)


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "date_added")
    search_fields = ("name",)
    list_filter = ("country",)
