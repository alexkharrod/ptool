"""
Management command: generate_web_content

Generates AI descriptions and/or keywords for products that are missing them.
Shares generation logic with import_from_sitemap.

Usage:
    python manage.py generate_web_content              # all missing
    python manage.py generate_web_content --dry-run    # preview
    python manage.py generate_web_content --limit 10   # first 10 missing
    python manage.py generate_web_content --sku EC18 TT01  # specific SKUs
    python manage.py generate_web_content --force      # regenerate even if set
    python manage.py generate_web_content --desc-only  # descriptions only
    python manage.py generate_web_content --kw-only    # keywords only
"""

import os
import time

from django.db.models import Q
from django.core.management.base import BaseCommand

from products.models import Product
from .import_from_sitemap import (
    generate_description_for_product,
    generate_keywords_for_product,
)


class Command(BaseCommand):
    help = "Generate AI descriptions and keywords for products missing them"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Preview which products would be processed without making API calls",
        )
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Only process N products",
        )
        parser.add_argument(
            "--sku", nargs="+", metavar="SKU",
            help="Only process specific SKUs",
        )
        parser.add_argument(
            "--force", action="store_true",
            help="Regenerate even if description/keywords already exist",
        )
        parser.add_argument(
            "--desc-only", action="store_true",
            help="Only generate descriptions (skip keywords)",
        )
        parser.add_argument(
            "--kw-only", action="store_true",
            help="Only generate keywords (skip descriptions)",
        )

    def handle(self, *args, **options):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key and not options["dry_run"]:
            self.stderr.write(self.style.ERROR("ANTHROPIC_API_KEY not set"))
            return

        dry_run = options["dry_run"]
        force = options["force"]
        desc_only = options["desc_only"]
        kw_only = options["kw_only"]

        # ── Build queryset ────────────────────────────────────────────────
        qs = Product.objects.all().order_by("sku")

        if options["sku"]:
            qs = qs.filter(sku__in=[s.upper() for s in options["sku"]])
        elif not force:
            # Only products missing description OR keywords
            qs = qs.filter(
                Q(website_description="") | Q(website_description__isnull=True) |
                Q(website_keywords="")    | Q(website_keywords__isnull=True)
            )

        if options["limit"]:
            qs = qs[:options["limit"]]

        total = qs.count()
        self.stdout.write(f"Products to process: {total}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no API calls will be made\n"))
            for p in qs:
                missing = []
                if not p.website_description:
                    missing.append("description")
                if not p.website_keywords:
                    missing.append("keywords")
                self.stdout.write(f"  {p.sku} — {p.name}  [missing: {', '.join(missing) or 'none (force mode)'}]")
            return

        # ── Generation loop ───────────────────────────────────────────────
        done = errors = 0

        for i, product in enumerate(qs, 1):
            self.stdout.write(f"[{i}/{total}] {product.sku} — {product.name}")
            try:
                updated = []

                if not kw_only and (force or not product.website_description):
                    self.stdout.write(f"  generating description...", ending="\r")
                    product.website_description = generate_description_for_product(product, api_key)
                    updated.append("description")

                if not desc_only and (force or not product.website_keywords):
                    self.stdout.write(f"  generating keywords...", ending="\r")
                    product.website_keywords = generate_keywords_for_product(product, api_key)
                    updated.append("keywords")

                if updated:
                    product.save(update_fields=["website_description", "website_keywords"])
                    self.stdout.write(self.style.SUCCESS(f"  ✓ generated: {', '.join(updated)}"))
                    time.sleep(0.5)  # gentle rate limiting
                else:
                    self.stdout.write(f"  nothing to update (already set)")

                done += 1

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  ✗ error: {e}"))
                errors += 1

        self.stdout.write("\n" + "─" * 40)
        self.stdout.write(self.style.SUCCESS(f"Done: {done}  Errors: {errors}"))
