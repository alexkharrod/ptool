from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0022_category_sku_seed"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="name",
            field=models.CharField(max_length=150, blank=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="moq",
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="package",
            field=models.CharField(max_length=50, blank=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="description",
            field=models.TextField(max_length=500, blank=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="carton_qty",
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="carton_weight",
            field=models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="carton_width",
            field=models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="carton_length",
            field=models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="carton_height",
            field=models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="air_freight",
            field=models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="ocean_freight",
            field=models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="duty_percent",
            field=models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="tariff_percent",
            field=models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="colors",
            field=models.CharField(max_length=150, blank=True),
        ),
    ]
