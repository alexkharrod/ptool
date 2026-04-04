"""
Management command: seed_hts_codes

Seeds the HtsCode table from the 'Claude HTS and Tariff info.xlsx' spreadsheet.
Safe to re-run — skips codes that already exist.

Usage:
    python manage.py seed_hts_codes
"""

from django.core.management.base import BaseCommand
from products.models import HtsCode

# (code, description, duty_pct, section_301_pct, notes, category_hint)
HTS_DATA = [
    ("8504.50.8000", "USB Charge Adapter without Battery",  0.0,   25.0,  "",                                                                                                  "Charging Tech"),
    ("8526.92.5000", "Wireless Finder / Air Tracker",       0.0,   25.0,  "AT01 @ 145%, AT05 avg to $1.00 with stock on 5/26(BF), AT16 - 145% for first shipment",            "Mobile Tech"),
    ("8205.51.1500", "Bottle Opener",                       0.0,   25.0,  "",                                                                                                  "Other"),
    ("8544.42.2000", "USB Cable",                           0.0,    0.0,  "CB62 avg to $0.14 with ocean stock, CB79 - higher tariff on averages stock 6/2",                   "Mobile Tech"),
    ("9002.11.9000", "Mobile Camera Lens",                  2.3,   25.0,  "",                                                                                                  "Mobile Tech"),
    ("8306.29.0000", "Metal Decoration",                    2.3,    0.0,  "",                                                                                                  "Other"),
    ("3926.90.9989", "Plastic Decoration",                  5.3,    7.5,  "",                                                                                                  "Other"),
    ("6302.93.1000", "Polyester Cooling Towel",             6.2,    0.0,  "",                                                                                                  "Personal Tech"),
    ("8528.69.3500", "Digital Photo Frame",                 0.0,    0.0,  "",                                                                                                  "Other"),
    ("9031.80.8085", "Distance Measurer",                   0.0,   25.0,  "",                                                                                                  "Personal Tech"),
    ("9617.00.1000", "Stainless Steel Drinkware",           7.2,    0.0,  "",                                                                                                  "Drinkware"),
    ("7615.19.00",   "Aluminum Drinkware",                  0.0,    0.0,  "",                                                                                                  "Drinkware"),
    ("8518.30.2000", "Wireless / Wired Earbuds",            0.0,    0.0,  "EB56 - no tariff on current. EB58 and EB59 (first 2K) - $2.18 on current inventory (first 5K)",    "Audio Tech"),
    ("4016.99.6050", "Silicone Case or Wallet",             2.5,   25.0,  "",                                                                                                  "Mobile Tech"),
    ("8308.10.0000", "Metal Clasp / Clip",                  0.0,   25.0,  "",                                                                                                  "Other"),
    ("8517.62.0000", "Wireless Headphone Splitter",         7.0,   25.0,  "",                                                                                                  "Audio Tech"),
    ("8414.59.6595", "Phone Fan",                           2.3,   25.0,  "",                                                                                                  "Mobile Tech"),
    ("8516.79.0000", "Battery Powered Hand Warmer",         2.7,    0.0,  "",                                                                                                  "Personal Tech"),
    ("4202.11.0090", "PU Case for Tablet / Pad",            8.0,   25.0,  "",                                                                                                  "Mobile Tech"),
    ("7616.99.5190", "Aluminum Phone Stand",                2.5,   50.0,  "",                                                                                                  "Mobile Tech"),
    ("8504.40.9540", "Power Bank 10000mAh",                 0.0,    7.5,  "JB66 - avg $1.47 on 6/2",                                                                          "Charging Tech"),
    ("8423.10.0010", "Digital Handheld Luggage Scale",      0.0,    0.0,  "",                                                                                                  "Personal Tech"),
    ("6307.90.9891", "Fabric Lanyards",                     7.0,    0.0,  "",                                                                                                  "Lanyards"),
    ("4202.92.9100", "Nylon / Fabric Bag",                 17.6,   25.0,  "",                                                                                                  "Personal Tech"),
    ("3924.90.5650", "Plastic Household Articles",          3.4,    7.5,  "",                                                                                                  "Other"),
    ("4420.90.8000", "Wood Articles",                       3.2,   25.0,  "",                                                                                                  "Other"),
    ("8517.62.0090", "Wireless Communication Devices",      7.5,    0.0,  "",                                                                                                  "Mobile Tech"),
    ("8518.10.80",   "Microphone",                          0.0,    7.5,  "",                                                                                                  "Audio Tech"),
    ("8531.20.0040", "Handheld Rewriteable Board",          0.0,   25.0,  "",                                                                                                  "Office Tech"),
    ("9019.10.2010", "Mini Battery Powered Massage Gun",    0.0,    0.0,  "MG04 - NO RT for stock 6/2",                                                                       "Personal Tech"),
    ("6307.10.1090", "Mouse Pad",                           4.1,    7.5,  "",                                                                                                  "Office Tech"),
    ("8523.51.0000", "NFC Stand / Smart Card",              0.0,    7.5,  "",                                                                                                  "Mobile Tech"),
    ("8471.60.9050", "Computer Mouse",                      0.0,   25.0,  "",                                                                                                  "Office Tech"),
    ("4202.92.4500", "Polyester Bag / Backpack",           20.0,   25.0,  "",                                                                                                  "Personal Tech"),
    ("9608.10.0000", "Pen / Stylus Pen",                    5.4,    7.5,  "Used $0.45",                                                                                        "Office Tech"),
    ("4202.31.6000", "PU Phone Wallet",                     8.0,   25.0,  "",                                                                                                  "Mobile Tech"),
    ("8531.10.0045", "Keychain Safety Alarm",               1.3,   25.0,  "",                                                                                                  "Personal Tech"),
    ("6307.10.2030", "Microfiber Glasses / Screen Cleaner", 5.3,    7.5,  "",                                                                                                  "Mobile Tech"),
    ("8518.29.8000", "Wireless Speaker",                    0.0,    7.5,  "SP76, SP88B, SP89B - no tariff on stock. SP94 - avg $0.25 more for 2k in stock",                   "Audio Tech"),
    ("8513.10.2000", "COB Flashlight / Torch",             12.5,    0.0,  "",                                                                                                  "Personal Tech"),
    ("8414.80.9000", "Battery Powered Car Tire Pump",       3.7,   25.0,  "",                                                                                                  "Personal Tech"),
    ("8473.30.5100", "Touch Stylus",                        0.0,   25.0,  "",                                                                                                  "Mobile Tech"),
    ("3910.00.0000", "Silicone Bubble Fidget",              3.0,   25.0,  "",                                                                                                  "Personal Tech"),
    ("9503.00.0090", "Toy Cube Fidget",                     0.0,    0.0,  "",                                                                                                  "Personal Tech"),
    ("8471.80.1000", "4-Port USB Hub",                      0.0,   25.0,  "",                                                                                                  "Office Tech"),
    ("3923.21.0095", "Dry Bag / Waterproof Bag",            3.0,   25.0,  "",                                                                                                  "Personal Tech"),
    ("8528.69.4500", "Video Projector (without tuner)",     0.0,    7.5,  "",                                                                                                  "Other"),
]


class Command(BaseCommand):
    help = "Seed HTS codes from Claude HTS and Tariff info spreadsheet"

    def handle(self, *args, **options):
        created = 0
        skipped = 0

        for code, description, duty, s301, notes, category in HTS_DATA:
            _, was_created = HtsCode.objects.get_or_create(
                code=code,
                defaults={
                    "description": description,
                    "duty_percent": duty,
                    "section_301_percent": s301,
                    "other_tariff_notes": notes,
                    "category_hint": category,
                }
            )
            if was_created:
                created += 1
                self.stdout.write(f"  Created: {code} — {description}")
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {created} HTS codes created, {skipped} already existed."
        ))
