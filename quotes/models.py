import os
from io import BytesIO

from django.apps import apps
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.timezone import now

from products.models import HtsCode, Vendor


# ── New quote system ──────────────────────────────────────────────────────────

class CustomerQuote(models.Model):
    STATUS_CHOICES = [
        ('draft',    'Draft'),
        ('sent',     'Sent'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    quote_number  = models.CharField(max_length=20, unique=True, blank=True)
    date          = models.DateField(default=now)
    customer_name = models.CharField(max_length=200)
    rep           = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='customer_quotes',
    )
    notes  = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.quote_number} — {self.customer_name}"

    def save(self, *args, **kwargs):
        if not self.quote_number:
            self.quote_number = self._next_quote_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _next_quote_number():
        from django.utils import timezone
        year = timezone.now().year
        prefix = f"Q-{year}-"
        last = (
            CustomerQuote.objects
            .filter(quote_number__startswith=prefix)
            .order_by('-quote_number')
            .values_list('quote_number', flat=True)
            .first()
        )
        if last:
            try:
                seq = int(last.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"


class QuoteLineItem(models.Model):
    quote       = models.ForeignKey(CustomerQuote, related_name='line_items', on_delete=models.CASCADE)
    product     = models.ForeignKey('products.Product', null=True, blank=True, on_delete=models.SET_NULL)
    sort_order  = models.PositiveIntegerField(default=0)

    # Overrides (pre-filled from product, editable per-quote)
    imprint_method = models.CharField(max_length=200, blank=True)
    setup_charge   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    run_charge     = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes          = models.TextField(blank=True)

    class Meta:
        ordering = ['sort_order', 'pk']

    def __str__(self):
        return f"Item {self.sort_order + 1}: {self.product}"

    @property
    def display_number(self):
        items = list(self.quote.line_items.values_list('pk', flat=True))
        try:
            return items.index(self.pk) + 1
        except ValueError:
            return '?'


class QuotePriceTier(models.Model):
    line_item   = models.ForeignKey(QuoteLineItem, related_name='tiers', on_delete=models.CASCADE)
    tier_number = models.PositiveSmallIntegerField()  # 1–5

    quantity     = models.PositiveIntegerField(default=0)
    unit_price   = models.DecimalField(max_digits=10, decimal_places=3, default=0)

    # Totals (not per-unit) — customer-facing landed cost for this qty
    air_total    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ocean_total  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    air_lead_time   = models.CharField(max_length=100, blank=True)
    ocean_lead_time = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['tier_number']
        unique_together = [('line_item', 'tier_number')]

    def __str__(self):
        return f"Tier {self.tier_number}: qty {self.quantity}"


def compress_image(image_field, max_width=800, quality=72):
    """Resize and compress an image in-place. Converts to JPEG."""
    from PIL import Image

    img = Image.open(image_field)

    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    output = BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    output.seek(0)
    return output.read()


# Create your models here.
class Quote(models.Model):
    quote_num = models.CharField(max_length=20, unique=True, null=False)
    name = models.CharField(max_length=150, default="Product Name")
    vendor = models.CharField(max_length=50, default="Vendor Name")
    vendor_part_number = models.CharField(max_length=50, default="Vendor Part Number")
    category = models.CharField(max_length=50, blank=True, default="")
    hts_code = models.ForeignKey(HtsCode, null=True, blank=True, on_delete=models.SET_NULL)
    vendor_ref = models.ForeignKey(Vendor, null=True, blank=True, on_delete=models.SET_NULL)
    image_url = models.CharField(
        max_length=2083, default="", blank=True
    )
    image = models.ImageField(upload_to="quotes/", null=True, blank=True)
    moq = models.IntegerField(default=0)
    package = models.CharField(max_length=50, default="White Box")
    production_time = models.CharField(max_length=50, default="MUST BE SPECIFIED")
    description = models.TextField(max_length=500, default="Description")

    customer_name = models.CharField(max_length=50, default="Customer Name")
    sales_rep = models.CharField(max_length=50, default="Sales Rep")

    # Master Carton info:
    carton_qty = models.IntegerField(default=0)
    carton_weight = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    carton_width = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    carton_length = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    carton_height = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    # Imprint info:
    imprint_location = models.CharField(max_length=50, default="Imprint Location")
    imprint_method = models.CharField(max_length=50, default="Imprint Method")
    imprint_dimension = models.CharField(max_length=50, default="Imprint Dimension")

    # Freight and Tariff Info:
    air_freight = models.TextField(max_length=500, default="Air Freight")
    ocean_freight = models.TextField(max_length=500, default="Ocean Freight")
    duty_percent = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    tariff_percent = models.DecimalField(max_digits=10, decimal_places=2, default=25.0)
    imprint_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.05)

    # Cost and Quote Fields:
    # quantities for quote
    quantity1 = models.IntegerField(default=0)
    quantity2 = models.IntegerField(default=0)
    quantity3 = models.IntegerField(default=0)
    quantity4 = models.IntegerField(default=0)
    quantity5 = models.IntegerField(default=0)

    # Unit Costs
    qty1_cost = models.DecimalField(max_digits=10, decimal_places=3, default=0.0)
    qty2_cost = models.DecimalField(max_digits=10, decimal_places=3, default=0.0)
    qty3_cost = models.DecimalField(max_digits=10, decimal_places=3, default=0.0)
    qty4_cost = models.DecimalField(max_digits=10, decimal_places=3, default=0.0)
    qty5_cost = models.DecimalField(max_digits=10, decimal_places=3, default=0.0)

    # Price via Air
    qty1_price_air = models.DecimalField(max_digits=10, decimal_places=3, default=0.0, blank=True, null=True)
    qty2_price_air = models.DecimalField(max_digits=10, decimal_places=3, default=0.0, blank=True, null=True)
    qty3_price_air = models.DecimalField(max_digits=10, decimal_places=3, default=0.0, blank=True, null=True)
    qty4_price_air = models.DecimalField(max_digits=10, decimal_places=3, default=0.0, blank=True, null=True)
    qty5_price_air = models.DecimalField(max_digits=10, decimal_places=3, default=0.0, blank=True, null=True)

    # Price via Ocean
    qty1_price_ocean = models.DecimalField(max_digits=10, decimal_places=3, default=0.0, blank=True, null=True)
    qty2_price_ocean = models.DecimalField(max_digits=10, decimal_places=3, default=0.0, blank=True, null=True)
    qty3_price_ocean = models.DecimalField(max_digits=10, decimal_places=3, default=0.0, blank=True, null=True)
    qty4_price_ocean = models.DecimalField(max_digits=10, decimal_places=3, default=0.0, blank=True, null=True)
    qty5_price_ocean = models.DecimalField(max_digits=10, decimal_places=3, default=0.0, blank=True, null=True)

    # Quote created data: DD-MM_YYYY
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Added', 'Added'),
        ('Closed', 'Closed'),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Open')
    date_created = models.DateTimeField(default=now, null=False, blank=False)

    air_transit_time = models.CharField(max_length=50, default="7-10 days")
    ocean_transit_time = models.CharField(max_length=50, default="~6 weeks")
    notes = models.CharField(max_length=255, blank=True, null=True)
    reciprocal_tariffs = models.CharField(max_length=255, blank=True, null=True)

    @property
    def display_name(self):
        """Returns the formatted quote label used for filenames and display: MDDYY - Rep - Name Quote"""
        d = self.date_created
        date_str = f"{d.month}{d.strftime('%d%y')}"
        safe_rep = self.sales_rep.strip().replace('"', '').replace('/', '-')
        safe_name = self.name.strip().replace('"', '').replace('/', '-')
        return f"{date_str} - {safe_rep} - {safe_name} Quote"

    def __str__(self):
        return self.quote_num

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
            old = Quote.objects.get(pk=self.pk)
            return old.image == self.image
        except Quote.DoesNotExist:
            return False
