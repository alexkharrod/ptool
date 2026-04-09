from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0024_product_source_show"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="date_published",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Date this product was first set to Published status.",
            ),
        ),
    ]
