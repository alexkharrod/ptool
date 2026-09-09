from django.db import models
from django.db.models import Q

from products.images import CompressedImageMixin




class Prospect(CompressedImageMixin, models.Model):
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

    # The "show" used for anything not found on a show floor: online finds, vendor
    # emails, samples in the mail. Selectable with one tap in the show banner.
    OFF_SHOW = "Off-Show"

    # Fields a quick floor capture usually leaves blank; the list's "Needs details"
    # filter and the card badge are driven by this one definition.
    DETAIL_FIELDS = ("unit_cost", "lead_time", "vendor_contact")

    class Meta:
        ordering = ["-date_added"]

    def __str__(self):
        return f"{self.product_name} — {self.vendor_name} ({self.show_name})"

    @classmethod
    def needs_details_q(cls):
        """Q object matching prospects with any DETAIL_FIELDS still blank."""
        q = Q()
        for f in cls.DETAIL_FIELDS:
            q |= Q(**{f: ""})
        return q

    @property
    def needs_details(self):
        return any(not getattr(self, f) for f in self.DETAIL_FIELDS)

    @property
    def missing_details(self):
        labels = {"unit_cost": "cost", "lead_time": "lead time", "vendor_contact": "contact"}
        return [labels[f] for f in self.DETAIL_FIELDS if not getattr(self, f)]

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

        super().save(*args, **kwargs)
