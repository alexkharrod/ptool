import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models
from django.utils.timezone import now


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


# Create your models here.
class Category(models.Model):
    code = models.CharField(max_length=10, unique=True)
    description = models.CharField(max_length=100)

    class Meta:
        ordering = ["code"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.code} – {self.description}"


class Vendor(models.Model):
    COUNTRY_CHOICES = [
        ("CN", "China"),
        ("US", "United States"),
        ("TW", "Taiwan"),
        ("VN", "Vietnam"),
        ("IN", "India"),
        ("OTHER", "Other"),
    ]

    name = models.CharField(max_length=100, unique=True)
    country = models.CharField(max_length=10, choices=COUNTRY_CHOICES, default="CN")
    date_added = models.DateTimeField(default=now)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class HtsCode(models.Model):
    CATEGORY_CHOICES = [
        ("Audio Tech", "Audio Tech"),
        ("Charging Tech", "Charging Tech"),
        ("Drinkware", "Drinkware"),
        ("Lanyards", "Lanyards"),
        ("Mobile Tech", "Mobile Tech"),
        ("Office Tech", "Office Tech"),
        ("Personal Tech", "Personal Tech"),
        ("USB Drives", "USB Drives"),
        ("Other", "Other"),
    ]

    code = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=200)
    duty_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    section_301_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    extra_tariff_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text="Extra/RT tariff rate (additional tariff beyond duty and Section 301)")
    other_tariff_notes = models.TextField(blank=True, help_text="Notes on additional tariffs, exemptions, or conditions (e.g. copper content rules)")
    category_hint = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True, help_text="Suggested product category for auto-suggest")
    date_added = models.DateTimeField(default=now)

    class Meta:
        ordering = ["code"]
        verbose_name = "HTS Code"
        verbose_name_plural = "HTS Codes"

    def __str__(self):
        return f"{self.code} — {self.description}"

    @property
    def total_percent(self):
        return self.duty_percent + self.section_301_percent + self.extra_tariff_percent


class ImprintMethod(models.Model):
    """
    A supported imprint method with standard setup and run charges.
    setup_fee=None means the fee is assigned individually per product (e.g. Mold Fee).
    run_charge=0 means no per-piece run charge (e.g. Sublimation, Mold Fee).
    """
    name = models.CharField(max_length=100, unique=True)
    setup_fee = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Leave blank for methods where fee is assigned per product (e.g. Mold Fee).",
    )
    run_charge = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Additional per-piece run charge (0 = none).",
    )
    sort_order = models.IntegerField(default=0, help_text="Display order in forms and NPDS.")

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    @property
    def has_variable_fee(self):
        """True when setup_fee must be assigned per product (i.e. Mold Fee)."""
        return self.setup_fee is None


class Product(models.Model):
    STATUS_CHOICES = [
        ("Open", "Open"),
        ("Published", "Published"),
        ("Canceled", "Canceled"),
    ]

    SOURCING_CHOICES = [
        ("overseas", "Overseas"),
        ("domestic", "US Domestic"),
        ("retail", "Retail"),
    ]

    sku = models.CharField(max_length=20, unique=True, null=False)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=50, blank=True)
    image_url = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to="products/", null=True, blank=True)
    moq = models.IntegerField()
    package = models.CharField(max_length=50)
    production_time = models.CharField(max_length=50)
    estimated_launch = models.CharField(max_length=50)
    description = models.TextField(max_length=500)

    # Vendor info:
    vendor = models.CharField(max_length=50)  # legacy text field — kept for backwards compat
    vendor_ref = models.ForeignKey(
        "Vendor", null=True, blank=True, on_delete=models.SET_NULL, related_name="products"
    )
    vendor_sku = models.CharField(max_length=50)

    # Master Carton info:
    carton_qty = models.IntegerField()
    carton_weight = models.DecimalField(max_digits=10, decimal_places=2)
    carton_width = models.DecimalField(max_digits=10, decimal_places=2)
    carton_length = models.DecimalField(max_digits=10, decimal_places=2)
    carton_height = models.DecimalField(max_digits=10, decimal_places=2)

    # Imprint info:
    imprint_location = models.CharField(max_length=50)
    imprint_method = models.CharField(max_length=50)   # legacy free-text field kept for existing data
    imprint_dimension = models.CharField(max_length=50)

    # Structured imprint methods (checkboxes on form, table on NPDS)
    imprint_methods = models.ManyToManyField(
        "ImprintMethod", blank=True, related_name="products",
    )
    mold_fee = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Setup fee for Mold Fee imprint (assigned individually per product).",
    )
    other_imprint = models.CharField(
        max_length=200, blank=True,
        help_text="Any additional imprint method not covered by the standard list.",
    )

    # AI-generated website content
    website_description = models.TextField(
        blank=True,
        help_text="AI-generated HTML description for the website (replaces specs on NPDS).",
    )
    website_keywords = models.TextField(
        blank=True,
        help_text="Comma-separated keyword phrases for product search (up to 30).",
    )

    # Sourcing
    sourcing = models.CharField(
        max_length=20, choices=SOURCING_CHOICES, default="overseas",
        help_text="Where this product is sourced/stocked from.",
    )
    needs_overseas_sku = models.BooleanField(
        default=False,
        help_text="US Domestic product that also needs an overseas (import) SKU created.",
    )

    # HTS code
    hts_code = models.ForeignKey(
        "HtsCode", null=True, blank=True, on_delete=models.SET_NULL, related_name="products"
    )

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

    date_created = models.DateTimeField(default=now)

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
