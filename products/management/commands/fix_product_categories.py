"""
Management command: fix_product_categories

Maps existing free-text category values (and SKU prefixes) to the new
standardised 2-letter category codes.

Run with --dry-run to preview changes without saving.
"""

from django.core.management.base import BaseCommand
from products.models import Product

VALID_CODES = {c[0] for c in Product.CATEGORY_CHOICES}

# Map old free-text values → new code (case-insensitive key)
TEXT_MAP = {
    "ac adapters": "AC",
    "ac adapter": "AC",
    "air trackers": "AT",
    "air tracker": "AT",
    "cables": "CB",
    "cable": "CB",
    "custom molds": "CM",
    "custom mold": "CM",
    "digital frames": "DF",
    "digital frame": "DF",
    "drinkware": "DW",
    "earbuds": "EB",
    "earbuds / headphones": "EB",
    "headphones": "EB",
    "fans": "FN",
    "fan": "FN",
    "fitness": "FT",
    "hand warmers": "HW",
    "hand warmer": "HW",
    "power banks": "JB",
    "power bank": "JB",
    "lanyards": "LY",
    "lanyard": "LY",
    "mobile accessories": "MA",
    "mobile": "MA",
    "is": "MA",
    "ph": "MA",
    "miscellaneous": "Misc",
    "misc": "Misc",
    "near field / rfid": "NFC",
    "nfc": "NFC",
    "rfid": "NFC",
    "office accessories": "OA",
    "office": "OA",
    "retail": "RT",
    "screen cleaners": "SC",
    "screen cleaner": "SC",
    "selfie lights": "SL",
    "selfie light": "SL",
    "speakers": "SP",
    "speaker": "SP",
    "straws": "ST",
    "straw": "ST",
    "travel adapters": "TA",
    "travel adapter": "TA",
    "tools": "TL",
    "tool": "TL",
    "fidget games": "TT",
    "fidget": "TT",
    "usb drives": "UD",
    "usb drive": "UD",
    "usb hubs": "UH",
    "usb hub": "UH",
    "wireless chargers": "WC",
    "wireless charger": "WC",
    "charging tech": "WC",
    "audio tech": "EB",
    "mobile tech": "MA",
    "office tech": "OA",
    "personal tech": "FT",
    "other": "Misc",
    "same as pk313": "Misc",
    "mg": "MG",
    "massage guns": "MG",
    "massage gun": "MG",
}


class Command(BaseCommand):
    help = "Remap product category values to standardised 2-letter codes"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        updated = 0
        already_ok = 0
        unmatched = []

        for product in Product.objects.all():
            cat = (product.category or "").strip()

            # Already a valid code — nothing to do
            if cat in VALID_CODES:
                already_ok += 1
                continue

            # Try text map first
            new_code = TEXT_MAP.get(cat.lower())

            # Fall back to SKU prefix (first 2 uppercase letters)
            if not new_code:
                prefix = "".join(c for c in product.sku if c.isalpha())[:2].upper()
                if prefix in VALID_CODES:
                    new_code = prefix

            if new_code:
                self.stdout.write(f"  {product.sku}: '{cat}' → '{new_code}'")
                if not dry_run:
                    product.category = new_code
                    product.save(update_fields=["category"])
                updated += 1
            else:
                unmatched.append(f"  {product.sku}: '{cat}' (no match found)")

        self.stdout.write(self.style.SUCCESS(
            f"\n{'DRY RUN — ' if dry_run else ''}Done. {updated} updated, {already_ok} already correct."
        ))
        if unmatched:
            self.stdout.write(self.style.WARNING(f"\n{len(unmatched)} unmatched — review manually:"))
            for line in unmatched:
                self.stdout.write(line)
