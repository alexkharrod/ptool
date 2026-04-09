from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quotes", "0021_salesrep"),
    ]

    operations = [
        # 1. Allow quote_number to be NULL (generated on first item add, not at creation)
        migrations.AlterField(
            model_name="customerquote",
            name="quote_number",
            field=models.CharField(blank=True, max_length=40, null=True, unique=True),
        ),

        # 2. Add internal freight cost fields to line items
        migrations.AddField(
            model_name="quotelineitem",
            name="our_air_freight",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="quotelineitem",
            name="our_ocean_freight",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
