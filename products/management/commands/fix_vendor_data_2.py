"""
Management command: fix_vendor_data_2

Second pass vendor cleanup — adds remaining new vendors and links all
outstanding unmatched products. Safe to re-run.

Usage:
    python manage.py fix_vendor_data_2 --dry-run
    python manage.py fix_vendor_data_2
"""

from django.core.management.base import BaseCommand
from products.models import Product, Vendor

# New vendors to create (all China unless noted)
NEW_VENDORS = [
    "Fulfillment Tech",
    "Bluetees",
    "Coral",
    "Webstraunt Store",
    "GetD",
    "SZ Xinchuang Lanteng Elec",
    "SKJ",
    "SZ Fengmang",
    "Yuyao Liuyang Appliance",
    "Caibo",
]

# SKU → canonical vendor name
SKU_OVERRIDES = {
    # Streamline → Fulfillment Tech
    "RT01":  "Fulfillment Tech",
    "RT09":  "Fulfillment Tech",
    "RT10":  "Fulfillment Tech",
    "RT11":  "Fulfillment Tech",
    "RT12":  "Fulfillment Tech",
    "RT13":  "Fulfillment Tech",
    "RT14":  "Fulfillment Tech",
    "RT15":  "Fulfillment Tech",
    "RT18":  "Fulfillment Tech",
    "RT25":  "Fulfillment Tech",
    "RT28":  "Fulfillment Tech",
    "RT29":  "Fulfillment Tech",
    # Bluetees
    "RT26":  "Bluetees",
    "RT27":  "Bluetees",
    "RT299": "Bluetees",
    "RT32":  "Bluetees",
    "RT41":  "Bluetees",
    # Others
    "RT06":  "Coral",
    "RT16":  "Webstraunt Store",
    "RT17":  "Webstraunt Store",
    "RT40":  "GetD",
    # Chinese manufacturers (name cleaned up)
    "DF24":  "SZ Xinchuang Lanteng Elec",
    "EB59":  "SKJ",
    "LY72":  "Dongguan Zhangeng Weaving",   # already in table
    "MA16":  "SZ Fengmang",
    "TL16":  "Yuyao Liuyang Appliance",
    "WC61":  "Caibo",
}

NEEDS_REVIEW = {}


class Command(BaseCommand):
    help = "Second-pass vendor cleanup: add remaining vendors and link outstanding products"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        if dry:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved\n"))

        # 1. Create new vendors
        self.stdout.write("-- Creating new vendors --")
        for name in NEW_VENDORS:
            exists = Vendor.objects.filter(name=name).exists()
            if not exists:
                if not dry:
                    Vendor.objects.create(name=name, country="CN")
                self.stdout.write(f"  {'[DRY]' if dry else '[OK]'} Created: {name}")
            else:
                self.stdout.write(f"  [SKIP] Already exists: {name}")

        # Rebuild map after creates
        vendor_map = {v.name.lower(): v for v in Vendor.objects.all()}

        # 2. Apply SKU overrides
        self.stdout.write("\n-- Linking products to vendors --")
        for sku, vendor_name in SKU_OVERRIDES.items():
            vendor_obj = vendor_map.get(vendor_name.lower())
            if not vendor_obj:
                self.stdout.write(self.style.ERROR(f"  [ERROR] Vendor not found: {vendor_name}"))
                continue
            try:
                product = Product.objects.get(sku=sku)
                self.stdout.write(
                    f"  {'[DRY]' if dry else '[OK]'} {sku}: '{product.vendor}' → {vendor_name}"
                )
                if not dry:
                    product.vendor = vendor_name
                    product.vendor_ref = vendor_obj
                    product.save(update_fields=["vendor", "vendor_ref"])
            except Product.DoesNotExist:
                self.stdout.write(f"  [SKIP] {sku} not found")

        # 3. Report SKUs still needing manual review
        if NEEDS_REVIEW:
            self.stdout.write(self.style.WARNING("\n-- Still needs manual review --"))
            for sku, text in NEEDS_REVIEW.items():
                self.stdout.write(f"  {sku}: '{text}' — assign vendor manually at /products/vendors/")

        self.stdout.write(self.style.SUCCESS("\nDone."))
