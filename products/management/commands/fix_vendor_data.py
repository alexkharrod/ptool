"""
Management command: fix_vendor_data

One-time cleanup of legacy vendor text fields:
  - Fixes typos/abbreviations to match existing Vendor records
  - Adds Carbon Tech as a new vendor
  - Sets LI for RT products with mixed/Apple vendor strings
  - Assigns Carbon Tech to RT04 / RT05
  - Deletes placeholder test SKUs

Usage:
    python manage.py fix_vendor_data --dry-run
    python manage.py fix_vendor_data
"""

from django.core.management.base import BaseCommand
from products.models import Product, Vendor


# Maps legacy vendor text (exact, case-sensitive) → canonical Vendor name
VENDOR_TEXT_FIXES = {
    # Abbreviations / typos pointing to existing vendors
    "Reflying":      "Shenzhen Reflying",
    "Power4":        "Power 4 Industries",
    "Moldull":       "Shenzhen Moldull",
    "SZ Moldull":    "Shenzhen Moldull",
    "HL":            "HongLiang",
    "Worldplug":     "World Plug",
    "WorldPLug":     "World Plug",
    "WorldPlug":     "World Plug",
}

# SKU → canonical Vendor name (overrides text matching)
SKU_VENDOR_OVERRIDES = {
    "RT04": "Carbon Tech",
    "RT05": "Carbon Tech",
    # RT products with apple/mixed sources → LI
    "RT03": "LI",
    "RT07": "LI",
    "RT08": "LI",
    "RT22": "LI",
    "RT23": "LI",
    "RT24": "LI",
    "RT31": "LI",
}

# Test/placeholder SKUs to delete
DELETE_SKUS = ["newsku", "newskuaa", "local sku", "test"]


class Command(BaseCommand):
    help = "One-time cleanup of legacy vendor text and test SKUs"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        if dry:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved\n"))

        # 1. Ensure Carbon Tech exists
        if not dry:
            carbon_tech, created = Vendor.objects.get_or_create(
                name="Carbon Tech", defaults={"country": "CN"}
            )
            if created:
                self.stdout.write("  Created vendor: Carbon Tech")
        else:
            self.stdout.write("  [DRY] Would create vendor: Carbon Tech (if missing)")

        # Build vendor lookup
        vendor_map = {v.name.lower(): v for v in Vendor.objects.all()}
        if dry:
            vendor_map["carbon tech"] = type("V", (), {"name": "Carbon Tech"})()

        # 2. Fix vendor text typos
        self.stdout.write("\n-- Fixing vendor text typos --")
        for bad_text, good_name in VENDOR_TEXT_FIXES.items():
            qs = Product.objects.filter(vendor=bad_text)
            vendor_obj = vendor_map.get(good_name.lower())
            for product in qs:
                self.stdout.write(f"  {'[DRY]' if dry else '[OK]'} {product.sku}: '{bad_text}' → {good_name}")
                if not dry:
                    product.vendor = good_name
                    product.vendor_ref = vendor_obj
                    product.save(update_fields=["vendor", "vendor_ref"])

        # 3. Apply SKU-level overrides
        self.stdout.write("\n-- Applying SKU-level vendor overrides --")
        for sku, vendor_name in SKU_VENDOR_OVERRIDES.items():
            vendor_obj = vendor_map.get(vendor_name.lower())
            try:
                product = Product.objects.get(sku=sku)
                self.stdout.write(f"  {'[DRY]' if dry else '[OK]'} {sku}: '{product.vendor}' → {vendor_name}")
                if not dry:
                    product.vendor = vendor_name
                    product.vendor_ref = vendor_obj
                    product.save(update_fields=["vendor", "vendor_ref"])
            except Product.DoesNotExist:
                self.stdout.write(f"  [SKIP] {sku} not found")

        # 4. Delete test SKUs
        self.stdout.write("\n-- Deleting test/placeholder SKUs --")
        for sku in DELETE_SKUS:
            try:
                product = Product.objects.get(sku=sku)
                self.stdout.write(f"  {'[DRY]' if dry else '[DELETED]'} {sku} ({product.name})")
                if not dry:
                    product.delete()
            except Product.DoesNotExist:
                self.stdout.write(f"  [SKIP] {sku} not found")

        self.stdout.write(self.style.SUCCESS("\nDone."))
