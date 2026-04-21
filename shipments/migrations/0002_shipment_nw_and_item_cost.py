from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shipments", "0001_initial"),
    ]

    operations = [
        # total_nw_kg on Shipment
        migrations.AddField(
            model_name="shipment",
            name="total_nw_kg",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Total net weight (kg)",
                max_digits=10,
                null=True,
            ),
        ),
        # unit_cost_usd on ShipmentItem
        migrations.AddField(
            model_name="shipmentitem",
            name="unit_cost_usd",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Unit cost from CI (USD) — internal, not shown to non-staff",
                max_digits=10,
                null=True,
            ),
        ),
    ]
