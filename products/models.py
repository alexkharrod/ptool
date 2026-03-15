import os
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models


def validate_image_size(image):
    """Reject uploads larger than 10 MB."""
    max_mb = 10
    if image.size > max_mb * 1024 * 1024:
        raise ValidationError(f"Image file too large — maximum size is {max_mb} MB.")


def compress_image(image_field, max_width=800, quality=72):
    """Resize and compress an image in-place. Converts to JPEG."""
    from PIL import Image

    img = Image.open(image_field)

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


class Category(models.Model):
    code = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ["code"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.code


class Product(models.Model):
    STATUS_CHOICES = [
        ("Open", "Open"),
        ("Added", "Added"),
        ("Canceled", "Canceled"),
    ]

    sku = models.CharField(max_length=20, unique=True, null=False)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=50)
    image_url = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to="products/", null=True, blank=True, validators=[validate_image_size])
    moq = models.IntegerField()
    package = models.CharField(max_length=50)
    production_time = models.CharField(max_length=50)
    estimated_launch = models.CharField(max_length=50)
    description = models.TextField(max_length=500)

    # Vendor info:
    vendor = models.CharField(max_length=50)
    vendor_sku = models.CharField(max_length=50)

    # Master Carton info:
    carton_qty = models.IntegerField()
    carton_weight = models.DecimalField(max_digits=10, decimal_places=2)
    carton_width = models.DecimalField(max_digits=10, decimal_places=2)
    carton_length = models.DecimalField(max_digits=10, decimal_places=2)
    carton_height = models.DecimalField(max_digits=10, decimal_places=2)

    # Imprint info:
    imprint_location = models.CharField(max_length=50)
    imprint_method = models.CharField(max_length=50)
    imprint_dimension = models.CharField(max_length=50)

    # Freight Costs
    air_freight = models.DecimalField(max_digits=10, decimal_places=2)
    ocean_freight = models.DecimalField(max_digits=10, decimal_places=2)
    duty_percent = models.DecimalField(max_digits=10, decimal_places=2)
    tariff_percent = models.DecimalField(max_digits=10, decimal_places=2)

    # To add checkboxes:
    price_list = models.BooleanField(default=False)
    product_list = models.BooleanField(default=False)
    hts_list = models.BooleanField(default=False)
    npds_done = models.BooleanField(default=False)
    qb_added = models.BooleanField(default=False)
    published = models.BooleanField(default=False)
    colors = models.CharField(max_length=150)

    # Product Status
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Open")

    def __str__(self):
        return f"{self.sku} — {self.name}"

    def save(self, *args, **kwargs):
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
            old = Product.objects.get(pk=self.pk)
            return old.image == self.image
        except Product.DoesNotExist:
            return False
