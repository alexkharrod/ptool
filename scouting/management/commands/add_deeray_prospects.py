"""
One-time command to seed 5 Deeraye Electronics mini cameras as prospects.

Source: Deeray Global_Mini Camera Quotation_2026.07.28.pdf
Vendor: Deeraye Electronics
FOB prices at 3,000 pcs minimum.

Usage:
    python manage.py add_deeray_prospects
    python manage.py add_deeray_prospects --dry-run
"""

from django.core.management.base import BaseCommand

from scouting.models import Prospect

VENDOR = {
    "vendor_name": "Deeraye Electronics",
    "vendor_contact": "Ellie",
    "vendor_email": "ellie@deerayelectronics.com",
    "vendor_website": "www.deerayelectronics.com",
    "show_name": "Deeray Global Quotation",
    "show_date": "2026-07-28",
}

PRODUCTS = [
    {
        "product_name": "Mini Camera X6",
        "unit_cost": "$4.50 @ 3,000 pcs FOB Shenzhen",
        "description": (
            "0.96\" LCD screen. 0.3MP resolution. 200mAh battery. "
            "Supports TF card (not included). "
            "Package: camera, USB-C cable, keychain, user manual. "
            "Dimensions: 60×23×20mm. Weight: 22g."
        ),
        "notes": "Item No. X6",
    },
    {
        "product_name": "Mini Camera MSG1",
        "unit_cost": "$5.70 @ 3,000 pcs FOB Shenzhen",
        "description": (
            "0.96\" HD screen (172×320). Video: 1080P/720P. Photo: 12M/2MP. "
            "200mAh battery. Supports TF card (not included). "
            "Package: camera, USB-C cable, keychain, user manual. "
            "Dimensions: 48×31×21.5mm. Weight: 22g."
        ),
        "notes": "Item No. MSG1",
    },
    {
        "product_name": "Mini Camera MSG2",
        "unit_cost": "$6.20 @ 3,000 pcs FOB Shenzhen",
        "description": (
            "0.96\" HD screen (172×320). Video: 1080P. Photo: 12M/2MP. "
            "70° lens angle. Built-in 180mAh battery (~115 min runtime). "
            "8 built-in beauty filters. Built-in mic. "
            "Type-C + TF card slot. Max 64GB storage. "
            "Dimensions: 42×28.5×33.7mm."
        ),
        "notes": "Item No. MSG2. Auto screen-off after 1 min. Op temp: -10°C–60°C.",
    },
    {
        "product_name": "Mini Camera G10",
        "unit_cost": "$12.30 @ 3,000 pcs FOB Shenzhen",
        "description": (
            "0.96\" LCD screen. 5MP resolution. 400mAh battery. "
            "Supports TF card (not included). "
            "Package: camera, USB-C cable, keychain, user manual. "
            "Dimensions: 22.4×22.4×72.3mm. Weight: 31.7g."
        ),
        "notes": "Item No. G10. Pen/tube form factor.",
    },
    {
        "product_name": "Mini Camera X7",
        "unit_cost": "$4.70 @ 3,000 pcs FOB Shenzhen",
        "description": (
            "0.96\" LCD screen. 1MP resolution. 200mAh battery. "
            "Supports TF card (not included). "
            "Package: camera, USB-C cable, keychain, user manual. "
            "Dimensions: 60×23×20mm. Weight: 22g."
        ),
        "notes": "Item No. X7.",
    },
]


class Command(BaseCommand):
    help = "Seed 5 Deeraye Electronics mini camera prospects (Deeray quotation 2026-07-28)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created without saving.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        created = 0
        skipped = 0

        for product in PRODUCTS:
            data = {**VENDOR, **product}
            name = data["product_name"]

            # Skip if a prospect with the same name + vendor already exists
            if Prospect.objects.filter(
                product_name=name, vendor_name=VENDOR["vendor_name"]
            ).exists():
                self.stdout.write(f"  SKIP (already exists): {name}")
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f"  DRY RUN — would create: {name} @ {data['unit_cost']}")
                created += 1
                continue

            Prospect.objects.create(
                show_name=data["show_name"],
                show_date=data["show_date"],
                vendor_name=data["vendor_name"],
                vendor_contact=data["vendor_contact"],
                vendor_email=data["vendor_email"],
                vendor_website=data["vendor_website"],
                product_name=name,
                description=data["description"],
                unit_cost=data["unit_cost"],
                notes=data["notes"],
                status="Spotted",
            )
            self.stdout.write(self.style.SUCCESS(f"  Created: {name}"))
            created += 1

        label = "Would create" if dry_run else "Created"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{label} {created} prospect(s), skipped {skipped} duplicate(s)."
            )
        )
