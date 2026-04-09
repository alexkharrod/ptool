from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0025_product_date_published"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="website_url",
            field=models.URLField(
                blank=True,
                help_text="Live URL of this product on logoincluded.com (e.g. https://www.logoincluded.com/product/…).",
            ),
        ),
    ]
