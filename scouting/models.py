import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models


def compress_image(image_field, max_width=800, quality=72):
    """Resize and compress an image in-place. Converts to JPEG.
    Applies EXIF orientation so portrait phone photos stay portrait."""
    from PIL import Image, ImageOps

    img = Image.open(image_field)

    # Honour EXIF rotation tag (fixes phone photos appearing sideways/upside-down)
    img = ImageOps.exif_transpose(img)

    # Convert palette/transparency modes to RGB for JPEG
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Resize if wider than max_width
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    output = BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    output.seek(0)
    return output.read()


class Prospect(models.Model):
    STATUS_CHOICES = [
        ("Spotted", "Spotted"),
        ("Sample Ordered", "Sample Ordered"),
        ("Evaluating", "Evaluating"),
        ("Adding", "Adding"),
        ("Rejected", "Rejected"),
    ]

    # Show info
    show_name = models.CharField(max_length=150)
    show_date = models.DateField(null=True, blank=True)

    # Vendor info
    vendor_name = models.CharField(max_length=150)
    vendor_contact = models.CharField(max_length=150, blank=True)
    vendor_email = models.CharField(max_length=150, blank=True)
    vendor_website = models.CharField(max_length=200, blank=True)

    # Product info
    product_name = models.CharField(max_length=150)
    description = models.TextField(max_length=500, blank=True)
    unit_cost = models.CharField(max_length=100, blank=True,
                                  help_text='e.g. "$2.50 @ 500 pcs"')
    colors = models.CharField(max_length=200, blank=True)
    lead_time = models.CharField(max_length=100, blank=True)
    notes = models.TextField(max_length=500, blank=True)

    # Image (stored in media/scouting/)
    image = models.ImageField(upload_to="scouting/", null=True, blank=True)

    # Reference number
    prospect_number = models.CharField(max_length=20, unique=True, blank=True)

    # Status & tracking
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default="Spotted"
    )
    date_added = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    # Promotion to full product
    promoted = models.BooleanField(default=False)
    promoted_sku = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["-date_added"]

    def __str__(self):
        return f"{self.product_name} — {self.vendor_name} ({self.show_name})"

    def save(self, *args, **kwargs):
        # Auto-assign prospect_number on first save
        if not self.prospect_number:
            last = (
                Prospect.objects.filter(prospect_number__startswith="PRO-")
                .order_by("prospect_number")
                .values_list("prospect_number", flat=True)
                .last()
            )
            if last:
                try:
                    next_num = int(last.split("-")[1]) + 1
                except (IndexError, ValueError):
                    next_num = 1
            else:
                next_num = 1
            self.prospect_number = f"PRO-{next_num:04d}"

        # Compress image on first upload or when image changes
        if self.image and not self._is_existing_image():
            original_name = os.path.splitext(
                os.path.basename(self.image.name)
            )[0]
            compressed = compress_image(self.image)
            new_name = f"{original_name}.jpg"
            self.image.save(new_name, ContentFile(compressed), save=False)
        super().save(*args, **kwargs)

    def _is_existing_image(self):
        """Returns True if this image is already stored (no re-compression needed)."""
        if not self.pk:
            return False
        try:
            old = Prospect.objects.get(pk=self.pk)
            return old.image == self.image
        except Prospect.DoesNotExist:
            return False
