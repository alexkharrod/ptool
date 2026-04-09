from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Shipment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("shipment_number", models.PositiveIntegerField(unique=True, help_text="Sequential shipment number (e.g. 118)")),
                ("ags_number", models.CharField(blank=True, max_length=50, help_text="AGS # from vendor invoice (e.g. SE00277382)")),
                ("po_numbers", models.CharField(blank=True, max_length=200, help_text="Comma-separated PO numbers covered by this shipment")),
                ("mode", models.CharField(choices=[("Air", "Air"), ("Ocean", "Ocean")], default="Ocean", max_length=10)),
                ("carrier", models.CharField(blank=True, max_length=100, help_text="e.g. ZIM, OOCL, FedEx")),
                ("vessel", models.CharField(blank=True, max_length=150, help_text="Vessel name & voyage (ocean only), e.g. 'ZIM Jade 3E / 18E'")),
                ("tracking_number", models.CharField(blank=True, max_length=100, help_text="AWB# (air) or container/BL# (ocean)")),
                ("etd", models.DateField(blank=True, null=True, help_text="Estimated Time of Departure")),
                ("eta_port", models.DateField(blank=True, null=True, help_text="ETA at US port")),
                ("eta_warehouse", models.DateField(blank=True, null=True, help_text="ETA at Cumming warehouse")),
                ("date_delivered", models.DateField(blank=True, null=True)),
                ("port_of_loading", models.CharField(blank=True, default="Shenzhen, China", max_length=100)),
                ("port_of_arrival", models.CharField(blank=True, choices=[("LA", "Los Angeles (LA)"), ("LB", "Long Beach (LB)"), ("SEA", "Seattle (SEA)"), ("NY", "New York (NY)"), ("SAV", "Savannah (SAV)"), ("MIA", "Miami (MIA)"), ("ATL", "Atlanta (ATL)"), ("Other", "Other")], max_length=10, help_text="US port of arrival")),
                ("status", models.CharField(choices=[("Ordered", "Ordered"), ("In Transit", "In Transit"), ("Arrived Port", "Arrived Port"), ("In Customs", "In Customs"), ("Out for Delivery", "Out for Delivery"), ("Delivered", "Delivered"), ("Cancelled", "Cancelled")], default="Ordered", max_length=30)),
                ("notes", models.TextField(blank=True)),
                ("total_cartons", models.PositiveIntegerField(blank=True, null=True)),
                ("total_pieces", models.PositiveIntegerField(blank=True, null=True)),
                ("total_cbm", models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True)),
                ("total_gw_kg", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, help_text="Total gross weight (kg)")),
                ("date_added", models.DateTimeField(auto_now_add=True)),
                ("date_updated", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-shipment_number"]},
        ),
        migrations.CreateModel(
            name="ShipmentItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("shipment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="shipments.shipment")),
                ("po_number", models.CharField(blank=True, max_length=50)),
                ("sku", models.CharField(blank=True, max_length=50, help_text="P/N or SKU")),
                ("description", models.CharField(blank=True, max_length=200)),
                ("cartons", models.PositiveIntegerField(blank=True, null=True)),
                ("qty", models.PositiveIntegerField(blank=True, null=True, help_text="Total pieces")),
                ("nw_kg", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, help_text="Net weight (kg)")),
                ("gw_kg", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, help_text="Gross weight (kg)")),
                ("cbm", models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True, help_text="Volume (CBM)")),
                ("dimensions_cm", models.CharField(blank=True, max_length=50, help_text="e.g. 34.5×34.5×21.5")),
            ],
            options={"ordering": ["pk"]},
        ),
        migrations.CreateModel(
            name="ShipmentDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("shipment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="shipments.shipment")),
                ("doc_type", models.CharField(choices=[("Packing List", "Packing List"), ("Invoice", "Invoice"), ("Bill of Lading", "Bill of Lading"), ("Customs Entry", "Customs Entry"), ("Other", "Other")], default="Packing List", max_length=30)),
                ("file", models.FileField(upload_to="shipments/docs/")),
                ("filename", models.CharField(blank=True, max_length=200)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["doc_type", "uploaded_at"]},
        ),
    ]
