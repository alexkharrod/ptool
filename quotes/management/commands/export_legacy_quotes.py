"""
Export every legacy `Quote` (the pre-April-2026 single-product quote system) to a
PDF, one file per quote, named:

    YYYY-MM-DD - <rep> - <quote #>.pdf

Idempotent: a file that already exists is skipped unless --overwrite is given.

    python manage.py export_legacy_quotes --dry-run
    python manage.py export_legacy_quotes
    python manage.py export_legacy_quotes --out "/some/other/folder"

Needs WeasyPrint's system libraries (pango etc.) on the machine running it.
Product images are fetched from Cloudinary; a quote whose image can't be
fetched is still exported, without the picture.
"""

import base64
import os
import re
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

from quotes.models import Quote

DEFAULT_OUT = "/Users/alex/Library/CloudStorage/Dropbox/LogoIncluded/Large Quotes"


def safe_component(text):
    """Make a string safe for a filename: strip path separators and odd punctuation."""
    text = (text or "").strip()
    text = re.sub(r'[\\/:*?"<>|]+', "-", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .-") or "unknown"


def pdf_filename(quote):
    date = quote.date_created.strftime("%Y-%m-%d")
    return f"{date} - {safe_component(quote.sales_rep)} - {safe_component(quote.quote_num)}.pdf"


def fetch_image_b64(quote):
    """Return the quote's product image as base64, or '' if there isn't one / it can't be read."""
    try:
        if quote.image:
            with urllib.request.urlopen(quote.image.url, timeout=20) as resp:
                return base64.b64encode(resp.read()).decode()
        if quote.image_url and not quote.image_url.startswith("http"):
            path = os.path.join(settings.BASE_DIR, "static", "images", quote.image_url)
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode()
    except Exception:
        pass
    return ""


def logo_b64():
    path = os.path.join(settings.BASE_DIR, "static", "images", "LI-Circle.png")
    if os.path.isfile(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


class Command(BaseCommand):
    help = "Export all legacy quotes to PDF files (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--out", default=DEFAULT_OUT, help=f"Output folder (default: {DEFAULT_OUT})")
        parser.add_argument("--dry-run", action="store_true", help="List what would be written; write nothing")
        parser.add_argument("--overwrite", action="store_true", help="Re-export files that already exist")

    def handle(self, *args, **opts):
        out = opts["out"]
        dry = opts["dry_run"]
        overwrite = opts["overwrite"]

        quotes = Quote.objects.order_by("date_created", "quote_num")
        total = quotes.count()
        self.stdout.write(f"{total} legacy quote(s) → {out}{'  [DRY RUN]' if dry else ''}")

        if not dry:
            os.makedirs(out, exist_ok=True)
            from weasyprint import HTML  # lazy: system libs may be missing

        logo = logo_b64()
        written = skipped = failed = 0
        for quote in quotes:
            name = pdf_filename(quote)
            path = os.path.join(out, name)
            if os.path.exists(path) and not overwrite:
                skipped += 1
                self.stdout.write(f"  skip   {name}  (exists)")
                continue
            if dry:
                self.stdout.write(f"  write  {name}")
                written += 1
                continue
            try:
                html = render_to_string("legacy_quote_pdf.html", {
                    "quote": quote,
                    "encoded_image": fetch_image_b64(quote),
                    "logo_b64": logo,
                })
                HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf(path, presentational_hints=True)
                written += 1
                self.stdout.write(f"  wrote  {name}")
            except Exception as e:  # keep going; report at the end
                failed += 1
                self.stderr.write(f"  FAILED {name}: {e}")

        self.stdout.write(self.style.SUCCESS(
            f"Done: {written} written, {skipped} skipped, {failed} failed."
        ))
