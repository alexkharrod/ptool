from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0016_category"),
    ]

    operations = [
        # Create the ImprintMethod lookup table
        migrations.CreateModel(
            name="ImprintMethod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("setup_fee", models.DecimalField(
                    blank=True, decimal_places=2, max_digits=8, null=True,
                    help_text="Leave blank for methods where fee is assigned per product (e.g. Mold Fee).",
                )),
                ("run_charge", models.DecimalField(
                    decimal_places=2, default=0, max_digits=8,
                    help_text="Additional per-piece run charge (0 = none).",
                )),
                ("sort_order", models.IntegerField(default=0, help_text="Display order in forms and NPDS.")),
            ],
            options={
                "ordering": ["sort_order", "name"],
            },
        ),
        # M2M: Product ↔ ImprintMethod
        migrations.AddField(
            model_name="product",
            name="imprint_methods",
            field=models.ManyToManyField(
                blank=True,
                related_name="products",
                to="products.imprintmethod",
            ),
        ),
        # Mold fee override (assigned individually per product)
        migrations.AddField(
            model_name="product",
            name="mold_fee",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True,
                help_text="Setup fee for Mold Fee imprint (assigned individually per product).",
            ),
        ),
        # Free-text "other" imprint method
        migrations.AddField(
            model_name="product",
            name="other_imprint",
            field=models.CharField(
                blank=True, max_length=200,
                help_text="Any additional imprint method not covered by the standard list.",
            ),
        ),
    ]
