from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0019_status_added_to_published"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="sourcing",
            field=models.CharField(
                choices=[
                    ("overseas", "Overseas"),
                    ("domestic", "US Domestic"),
                    ("retail", "Retail"),
                ],
                default="overseas",
                help_text="Where this product is sourced/stocked from.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="needs_overseas_sku",
            field=models.BooleanField(
                default=False,
                help_text="US Domestic product that also needs an overseas (import) SKU created.",
            ),
        ),
    ]
