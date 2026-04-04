from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0011_vendor_product_vendor_ref"),
    ]

    operations = [
        migrations.CreateModel(
            name="HtsCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20, unique=True)),
                ("description", models.CharField(max_length=200)),
                ("duty_percent", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("section_301_percent", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("other_tariff_notes", models.TextField(blank=True)),
                ("category_hint", models.CharField(
                    blank=True,
                    choices=[
                        ("Audio Tech", "Audio Tech"),
                        ("Charging Tech", "Charging Tech"),
                        ("Drinkware", "Drinkware"),
                        ("Lanyards", "Lanyards"),
                        ("Mobile Tech", "Mobile Tech"),
                        ("Office Tech", "Office Tech"),
                        ("Personal Tech", "Personal Tech"),
                        ("USB Drives", "USB Drives"),
                        ("Other", "Other"),
                    ],
                    max_length=50,
                )),
                ("date_added", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={"ordering": ["code"], "verbose_name": "HTS Code", "verbose_name_plural": "HTS Codes"},
        ),
        migrations.AddField(
            model_name="product",
            name="hts_code",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="products",
                to="products.htscode",
            ),
        ),
    ]
