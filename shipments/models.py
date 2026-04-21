from django.db import models


class Shipment(models.Model):
    MODE_AIR = "Air"
    MODE_OCEAN = "Ocean"
    MODE_CHOICES = [
        (MODE_AIR, "Air"),
        (MODE_OCEAN, "Ocean"),
    ]

    STATUS_CHOICES = [
        ("Ordered", "Ordered"),
        ("In Transit", "In Transit"),
        ("Arrived Port", "Arrived Port"),
        ("In Customs", "In Customs"),
        ("Out for Delivery", "Out for Delivery"),
        ("Delivered", "Delivered"),
        ("Cancelled", "Cancelled"),
    ]

    PORT_CHOICES = [
        ("LA", "Los Angeles (LA)"),
        ("LB", "Long Beach (LB)"),
        ("SEA", "Seattle (SEA)"),
        ("NY", "New York (NY)"),
        ("SAV", "Savannah (SAV)"),
        ("MIA", "Miami (MIA)"),
        ("ATL", "Atlanta (ATL)"),
        ("Other", "Other"),
    ]

    # ── Identification ──────────────────────────────────────────────────────
    shipment_number = models.PositiveIntegerField(
        unique=True,
        help_text="Sequential shipment number (e.g. 118)",
    )
    ags_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="AGS # from vendor invoice (e.g. SE00277382)",
    )
    po_numbers = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma-separated PO numbers covered by this shipment",
    )

    # ── Mode & carrier ──────────────────────────────────────────────────────
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default=MODE_OCEAN)
    carrier = models.CharField(max_length=100, blank=True, help_text="e.g. ZIM, OOCL, FedEx")
    vessel = models.CharField(
        max_length=150,
        blank=True,
        help_text="Vessel name & voyage (ocean only), e.g. 'ZIM Jade 3E / 18E'",
    )
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="AWB# (air) or container/BL# (ocean)",
    )

    # ── Dates ───────────────────────────────────────────────────────────────
    etd = models.DateField(null=True, blank=True, help_text="Estimated Time of Departure")
    eta_port = models.DateField(null=True, blank=True, help_text="ETA at US port")
    eta_warehouse = models.DateField(
        null=True, blank=True, help_text="ETA at Cumming warehouse"
    )
    date_delivered = models.DateField(null=True, blank=True)

    # ── Routing ─────────────────────────────────────────────────────────────
    port_of_loading = models.CharField(
        max_length=100, blank=True, default="Shenzhen, China"
    )
    port_of_arrival = models.CharField(
        max_length=10,
        choices=PORT_CHOICES,
        blank=True,
        help_text="US port of arrival",
    )

    # ── Status & notes ──────────────────────────────────────────────────────
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default="Ordered"
    )
    notes = models.TextField(blank=True)

    # ── Totals (filled from packing list) ───────────────────────────────────
    total_cartons = models.PositiveIntegerField(null=True, blank=True)
    total_pieces = models.PositiveIntegerField(null=True, blank=True)
    total_cbm = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    total_nw_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Total net weight (kg)",
    )
    total_gw_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Total gross weight (kg)",
    )

    # ── Audit ───────────────────────────────────────────────────────────────
    date_added = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-shipment_number"]

    def __str__(self):
        ags = f" / {self.ags_number}" if self.ags_number else ""
        return f"#{self.shipment_number}{ags} — {self.carrier or self.mode}"

    @classmethod
    def next_shipment_number(cls):
        """Return the next available sequential shipment number."""
        last = cls.objects.order_by("-shipment_number").first()
        return (last.shipment_number + 1) if last else 101


class ShipmentItem(models.Model):
    """One line item from a packing list tied to a shipment."""

    shipment = models.ForeignKey(
        Shipment, on_delete=models.CASCADE, related_name="items"
    )
    po_number = models.CharField(max_length=50, blank=True)
    sku = models.CharField(max_length=50, blank=True, help_text="P/N or SKU")
    description = models.CharField(max_length=200, blank=True)
    cartons = models.PositiveIntegerField(null=True, blank=True)
    qty = models.PositiveIntegerField(null=True, blank=True, help_text="Total pieces")
    nw_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Net weight (kg)",
    )
    gw_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Gross weight (kg)",
    )
    cbm = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        help_text="Volume (CBM)",
    )
    dimensions_cm = models.CharField(
        max_length=50, blank=True, help_text="e.g. 34.5×34.5×21.5"
    )
    unit_cost_usd = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        help_text="Unit cost from CI (USD) — internal, not shown to non-staff",
    )

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return f"{self.sku or '—'} × {self.qty or '?'} pcs ({self.shipment})"


class ShipmentDocument(models.Model):
    """Attached file (packing list, invoice, BOL, etc.) for a shipment."""

    DOC_TYPE_CHOICES = [
        ("Packing List", "Packing List"),
        ("Invoice", "Invoice"),
        ("Bill of Lading", "Bill of Lading"),
        ("Customs Entry", "Customs Entry"),
        ("Other", "Other"),
    ]

    shipment = models.ForeignKey(
        Shipment, on_delete=models.CASCADE, related_name="documents"
    )
    doc_type = models.CharField(
        max_length=30, choices=DOC_TYPE_CHOICES, default="Packing List"
    )
    file = models.FileField(upload_to="shipments/docs/")
    filename = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["doc_type", "uploaded_at"]

    def __str__(self):
        return f"{self.doc_type} — {self.shipment}"

    def save(self, *args, **kwargs):
        if self.file and not self.filename:
            import os
            self.filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)
