"""
Management command: seed_vendors

Seeds the Vendor table from the known vendor list extracted from the
product gap spreadsheet. Safe to re-run — skips any that already exist.

Usage:
    python manage.py seed_vendors
"""

from django.core.management.base import BaseCommand
from products.models import Vendor

VENDORS = [
    "A-Clover Promo",
    "Aiyos",
    "Bluefin",
    "Bothwinner",
    "China World Connection (HK) Co., Ltd",
    "Cstar",
    "DT",
    "DoTech",
    "Dongguan Fulida",
    "Dongguan Lead Silicone",
    "Dongguan Zhangeng Weaving",
    "GBE",
    "Goodwin",
    "Gotodo",
    "HongKang Capital",
    "HongLiang",
    "LI",
    "Mossloo",
    "Ningbo Diya",
    "PopStation",
    "Power 4 Industries",
    "RGK",
    "RSH",
    "SKL",
    "SZ Chuangxinjia Smart Card",
    "SZ Laudtec Electronics",
    "Shenzhen Moldull",
    "Shenzhen Reflying",
    "UEMade",
    "Wontravel",
    "World Plug",
]


class Command(BaseCommand):
    help = "Seed the Vendor table from the initial product gap spreadsheet"

    def handle(self, *args, **options):
        created = 0
        skipped = 0
        for name in VENDORS:
            _, was_created = Vendor.objects.get_or_create(name=name, defaults={"country": "CN"})
            if was_created:
                created += 1
                self.stdout.write(f"  Created: {name}")
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {created} vendors created, {skipped} already existed."
        ))
