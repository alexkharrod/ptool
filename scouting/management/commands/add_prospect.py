"""
One-shot management command to add a scouting prospect.
Run from the ptool project root:

    python manage.py add_prospect
    python manage.py add_prospect --image /path/to/photo.jpg

If no --image is given, the command automatically checks scouting/inbox/
for any image file and uses the first one it finds (then removes it).
"""
import glob
import os
from datetime import date

from django.core.management.base import BaseCommand

from scouting.models import Prospect

INBOX_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "inbox")
IMAGE_EXTS = ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.gif")


def find_inbox_image():
    for ext in IMAGE_EXTS:
        matches = glob.glob(os.path.join(INBOX_DIR, ext))
        matches += glob.glob(os.path.join(INBOX_DIR, ext.upper()))
        if matches:
            return matches[0]
    return None


class Command(BaseCommand):
    help = "Add a scouting prospect. Auto-picks up image from scouting/inbox/ if present."

    def add_arguments(self, parser):
        parser.add_argument(
            "--image",
            type=str,
            default=None,
            help="Path to a product photo. If omitted, checks scouting/inbox/ automatically.",
        )

    def handle(self, *args, **options):
        p = Prospect(
            show_name="Just Sourcing",
            show_date=date(2026, 3, 19),
            vendor_name="DT",
            vendor_contact="Annie",
            product_name="Magnetic Dashboard Car Phone Mount",
            description=(
                "270°+270° dual-axis tilt, 360° base rotation, "
                "one-button device release (PUSH), power switch. "
                "MagSafe-compatible magnetic ring."
            ),
            unit_cost="$9.90 @ 100 pcs",
            lead_time="7–10 working days",
            notes="MOQ: 100 pcs | Packing: 100 pcs/ctn | GW: 23 KG | Carton: 66×36.5×39 cm",
            status="Spotted",
        )

        image_path = options.get("image") or find_inbox_image()
        if image_path:
            image_path = os.path.expanduser(image_path)
            if os.path.exists(image_path):
                from django.core.files import File
                with open(image_path, "rb") as f:
                    p.image.save(os.path.basename(image_path), File(f), save=False)
                self.stdout.write(f"  Image: {os.path.basename(image_path)}")
                # Clean up inbox after use
                if not options.get("image") and os.path.abspath(image_path).startswith(
                    os.path.abspath(INBOX_DIR)
                ):
                    os.remove(image_path)
                    self.stdout.write("  Inbox cleared.")
            else:
                self.stdout.write(self.style.WARNING(f"  Image not found: {image_path} — skipping"))
        else:
            self.stdout.write(self.style.WARNING("  No image found — saving without photo."))

        p.save()
        self.stdout.write(self.style.SUCCESS(f"✓ Saved: {p} (id={p.pk})"))
