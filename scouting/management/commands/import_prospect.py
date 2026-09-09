"""
Management command for importing a scouting prospect.

Usage:
    python manage.py import_prospect \
        --show "HKTDC April 2026" \
        --show-date "2026-04-15" \
        --vendor "Acme Promo Co." \
        --vendor-contact "John Li" \
        --vendor-email "john@acmepromo.com" \
        --vendor-website "www.acmepromo.com" \
        --product "Silicone Foldable Water Bottle 600ml" \
        --description "BPA-free silicone, collapses flat, carabiner clip included" \
        --cost "$3.20 @ 500 pcs / $2.80 @ 1000 pcs" \
        --colors "Black, Navy, Red, Forest Green" \
        --lead-time "45-60 days" \
        --notes "Popular item at show, ask for sample in black" \
        --image "/path/to/photo.jpg" \
        --status "Sample Ordered"
"""

import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from scouting.models import Prospect
from products.images import compress_image
from django.core.files.base import ContentFile


class Command(BaseCommand):
    help = "Import a scouting prospect from trade show notes."

    def add_arguments(self, parser):
        parser.add_argument("--show", required=True, help="Show / event name")
        parser.add_argument("--show-date", default="", help="Show date (YYYY-MM-DD)")
        parser.add_argument("--vendor", required=True, help="Vendor name")
        parser.add_argument("--vendor-contact", default="", help="Vendor contact name")
        parser.add_argument("--vendor-email", default="", help="Vendor email")
        parser.add_argument("--vendor-website", default="", help="Vendor website")
        parser.add_argument("--product", required=True, help="Product name / description")
        parser.add_argument("--description", default="", help="Product specifications")
        parser.add_argument("--cost", default="", help='Cost as seen, e.g. "$2.50 @ 500 pcs"')
        parser.add_argument("--colors", default="", help="Available colors")
        parser.add_argument("--lead-time", default="", help="Lead time")
        parser.add_argument("--notes", default="", help="Additional notes")
        parser.add_argument("--image", default="", help="Path to product photo on disk")
        parser.add_argument(
            "--status",
            default="Spotted",
            choices=["Spotted", "Sample Ordered", "Evaluating", "Adding", "Rejected"],
            help="Initial status",
        )

    def handle(self, *args, **options):
        # Build prospect
        prospect = Prospect(
            show_name=options["show"],
            vendor_name=options["vendor"],
            vendor_contact=options.get("vendor_contact", ""),
            vendor_email=options.get("vendor_email", ""),
            vendor_website=options.get("vendor_website", ""),
            product_name=options["product"],
            description=options.get("description", ""),
            unit_cost=options.get("cost", ""),
            colors=options.get("colors", ""),
            lead_time=options.get("lead_time", ""),
            notes=options.get("notes", ""),
            status=options["status"],
        )

        # Handle show date
        show_date_str = options.get("show_date", "")
        if show_date_str:
            from datetime import date
            try:
                parts = show_date_str.split("-")
                prospect.show_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except (ValueError, IndexError):
                self.stdout.write(
                    self.style.WARNING(f"Invalid date format '{show_date_str}' — skipping.")
                )

        # Handle image: compress and attach
        image_path = options.get("image", "")
        if image_path:
            if not os.path.exists(image_path):
                raise CommandError(f"Image file not found: {image_path}")
            original_name = os.path.splitext(os.path.basename(image_path))[0]
            with open(image_path, "rb") as f:
                from django.core.files.uploadedfile import SimpleUploadedFile
                # Compress before saving
                compressed_bytes = compress_image(f)
                uploaded = SimpleUploadedFile(
                    f"{original_name}.jpg",
                    compressed_bytes,
                    content_type="image/jpeg",
                )
            prospect.image = uploaded

        # Save — model.save() handles compression check
        prospect.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Prospect #{prospect.pk} created: {prospect.product_name} "
                f"({prospect.vendor_name} / {prospect.show_name})"
            )
        )
        if prospect.image:
            self.stdout.write(f"  Image saved: {prospect.image.name}")
