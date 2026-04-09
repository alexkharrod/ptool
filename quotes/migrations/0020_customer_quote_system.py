import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quotes", "0019_alter_quote_category"),
        ("products", "0026_product_website_url"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerQuote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quote_number",  models.CharField(blank=True, max_length=20, unique=True)),
                ("date",          models.DateField(default=django.utils.timezone.now)),
                ("customer_name", models.CharField(max_length=200)),
                ("notes",         models.TextField(blank=True)),
                ("status",        models.CharField(
                    choices=[
                        ("draft",    "Draft"),
                        ("sent",     "Sent"),
                        ("accepted", "Accepted"),
                        ("declined", "Declined"),
                    ],
                    default="draft",
                    max_length=20,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("rep", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="customer_quotes",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="QuoteLineItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order",     models.PositiveIntegerField(default=0)),
                ("imprint_method", models.CharField(blank=True, max_length=200)),
                ("setup_charge",   models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("run_charge",     models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("notes",          models.TextField(blank=True)),
                ("quote", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="line_items",
                    to="quotes.customerquote",
                )),
                ("product", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to="products.product",
                )),
            ],
            options={"ordering": ["sort_order", "pk"]},
        ),
        migrations.CreateModel(
            name="QuotePriceTier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tier_number",     models.PositiveSmallIntegerField()),
                ("quantity",        models.PositiveIntegerField(default=0)),
                ("unit_price",      models.DecimalField(decimal_places=3, default=0, max_digits=10)),
                ("air_total",       models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("ocean_total",     models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("air_lead_time",   models.CharField(blank=True, max_length=100)),
                ("ocean_lead_time", models.CharField(blank=True, max_length=100)),
                ("line_item", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="tiers",
                    to="quotes.quotelineitem",
                )),
            ],
            options={"ordering": ["tier_number"]},
        ),
        migrations.AddConstraint(
            model_name="quotepricetier",
            constraint=models.UniqueConstraint(
                fields=["line_item", "tier_number"],
                name="unique_tier_per_item",
            ),
        ),
    ]
