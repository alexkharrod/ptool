from django.contrib import admin

from .models import Category, ImprintMethod, Product, Vendor, HtsCode

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


@admin.register(ImprintMethod)
class ImprintMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "setup_fee", "run_charge", "sort_order")
    ordering = ("sort_order", "name")


@admin.register(HtsCode)
class HtsCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "duty_percent", "section_301_percent", "extra_tariff_percent", "rates_verified_date")
    search_fields = ("code", "description")
    list_filter = ("categories",)
    fields = ("code", "description", "duty_percent", "section_301_percent", "extra_tariff_percent", "other_tariff_notes", "categories", "rates_verified_date")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "sku_seed")
    search_fields = ("code", "description")
    ordering = ("code",)


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "date_added")
    search_fields = ("name",)
    list_filter = ("country",)
