from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0010_product_date_created"),
    ]

    operations = [
        migrations.CreateModel(
            name="Vendor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("country", models.CharField(
                    choices=[
                        ("CN", "China"),
                        ("US", "United States"),
                        ("TW", "Taiwan"),
                        ("VN", "Vietnam"),
                        ("IN", "India"),
                        ("OTHER", "Other"),
                    ],
                    default="CN",
                    max_length=10,
                )),
                ("date_added", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddField(
            model_name="product",
            name="vendor_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="products",
                to="products.vendor",
            ),
        ),
    ]
