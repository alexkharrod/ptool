"""
Management command: link_vendor_refs

Matches each Product's legacy `vendor` text field to a Vendor record
and sets the `vendor_ref` FK. Safe to re-run — skips products already linked.

Usage:
    python manage.py link_vendor_refs           # live run
    python manage.py link_vendor_refs --dry-run # preview only
"""

from django.core.management.base import BaseCommand
from products.models import Product, Vendor


class Command(BaseCommand):
    help = "Link Product.vendor_ref FK from legacy vendor text field"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview matches without saving anything",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved\n"))

        # Build a case-insensitive lookup map of all vendors
        vendor_map = {v.name.lower(): v for v in Vendor.objects.all()}

        linked = 0
        skipped = 0
        unmatched = []

        products = Product.objects.filter(vendor_ref__isnull=True).exclude(vendor="")

        for product in products:
            vendor_text = product.vendor.strip()
            vendor = vendor_map.get(vendor_text.lower())

            if vendor:
                if not dry_run:
                    product.vendor_ref = vendor
                    product.save(update_fields=["vendor_ref"])
                self.stdout.write(f"  {'[DRY]' if dry_run else '[OK]'} {product.sku} → {vendor.name}")
                linked += 1
            else:
                unmatched.append((product.sku, vendor_text))
                skipped += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Linked: {linked}"))

        if unmatched:
            self.stdout.write(self.style.WARNING(f"Unmatched ({skipped}) — vendor text not found in Vendor table:"))
            for sku, text in sorted(unmatched):
                self.stdout.write(f"  {sku}: '{text}'")
            self.stdout.write(
                "\nTip: Add missing vendors at /products/vendors/add/ then re-run this command."
            )
        else:
            self.stdout.write("All products matched.")
