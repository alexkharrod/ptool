from django.core.management.base import BaseCommand
from products.models import Category

CATEGORIES = [
    ("AC", "AC Adapters"),
    ("AT", "Air Trackers"),
    ("CB", "Cables"),
    ("CM", "Custom Molds"),
    ("DF", "Digital Frames"),
    ("DW", "Drinkware"),
    ("EB", "Earbuds / Headphones"),
    ("FN", "Fans"),
    ("FT", "Fitness"),
    ("HW", "Hand Warmers"),
    ("JB", "Power Banks"),
    ("LY", "Lanyards"),
    ("MA", "Mobile Accessories"),
    ("MG", "Massage Guns"),
    ("Misc", "Miscellaneous"),
    ("NFC", "Near Field / RFID"),
    ("OA", "Office Accessories"),
    ("RT", "Retail"),
    ("SC", "Screen Cleaners"),
    ("SL", "Selfie Lights"),
    ("SP", "Speakers"),
    ("ST", "Straws"),
    ("TA", "Travel Adapters"),
    ("TL", "Tools"),
    ("TT", "Fidget Games"),
    ("UD", "USB Drives"),
    ("UH", "USB Hubs"),
    ("WC", "Wireless Chargers"),
]


class Command(BaseCommand):
    help = "Seed the Category table with standard product categories"

    def handle(self, *args, **options):
        created = updated = 0
        for code, description in CATEGORIES:
            obj, was_created = Category.objects.get_or_create(code=code)
            obj.description = description
            obj.save()
            if was_created:
                created += 1
                self.stdout.write(f"  Created: {code} – {description}")
            else:
                updated += 1
                self.stdout.write(f"  OK: {code} – {description}")
        self.stdout.write(self.style.SUCCESS(f"\nDone. {created} created, {updated} already existed."))
