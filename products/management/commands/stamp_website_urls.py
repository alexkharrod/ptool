"""
Management command: stamp_website_urls

Reads the logoincluded.com sitemap and stamps the live product URL onto any
existing Product record that doesn't yet have a website_url.

Safe to run multiple times — skips products that already have a URL set.

Usage:
    python manage.py stamp_website_urls              # stamp all missing URLs
    python manage.py stamp_website_urls --dry-run    # preview only
    python manage.py stamp_website_urls --overwrite  # update even if already set
    python manage.py stamp_website_urls --sku EB59 LY1302  # specific SKUs only
"""

from django.core.management.base import BaseCommand

from products.management.commands.import_from_sitemap import fetch_sitemap_products
from products.models import Product


class Command(BaseCommand):
    help = "Stamp website_url on existing products from the logoincluded.com sitemap"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Preview what would be updated without saving anything.",
        )
        parser.add_argument(
            "--overwrite", action="store_true",
            help="Update website_url even on products that already have one set.",
        )
        parser.add_argument(
            "--sku", nargs="+", metavar="SKU",
            help="Only process specified SKUs (e.g. --sku EB59 LY1302).",
        )

    def handle(self, *args, **options):
        dry_run   = options["dry_run"]
        overwrite = options["overwrite"]
        only_skus = {s.upper() for s in options["sku"]} if options["sku"] else None

        self.stdout.write("Fetching sitemap from logoincluded.com…")
        try:
            sitemap_products = fetch_sitemap_products()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to fetch sitemap: {e}"))
            return

        self.stdout.write(f"Sitemap contains {len(sitemap_products)} product URLs")

        # Build a SKU → URL lookup from the sitemap
        sku_to_url = {p["sku"]: p["product_url"] for p in sitemap_products}

        if only_skus:
            sku_to_url = {k: v for k, v in sku_to_url.items() if k in only_skus}
            self.stdout.write(f"Filtered to {len(sku_to_url)} specified SKU(s)")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — nothing will be saved\n"))

        updated = skipped = not_found = 0

        # Iterate over the DB products we can match
        qs = Product.objects.filter(sku__in=sku_to_url.keys())

        for product in qs.order_by("sku"):
            url = sku_to_url[product.sku]

            if product.website_url and not overwrite:
                self.stdout.write(f"  {product.sku} — already has URL, skipping")
                skipped += 1
                continue

            action = "would set" if dry_run else "setting"
            self.stdout.write(f"  {product.sku} — {action} → {url}")

            if not dry_run:
                product.website_url = url
                product.save(update_fields=["website_url"])

            updated += 1

        # Report any sitemap SKUs not found in the DB
        db_skus = set(Product.objects.values_list("sku", flat=True))
        for sku in sorted(sku_to_url.keys()):
            if sku not in db_skus:
                not_found += 1

        self.stdout.write("\n" + "─" * 40)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN complete"))
            self.stdout.write(f"  Would update : {updated}")
            self.stdout.write(f"  Would skip   : {skipped} (already have URL)")
        else:
            self.stdout.write(self.style.SUCCESS("Stamp complete"))
            self.stdout.write(f"  Updated : {updated}")
            self.stdout.write(f"  Skipped : {skipped} (already had URL)")
        if not_found:
            self.stdout.write(
                self.style.WARNING(f"  Sitemap SKUs not in DB : {not_found} "
                                   f"(run import_from_sitemap to add them)")
            )
