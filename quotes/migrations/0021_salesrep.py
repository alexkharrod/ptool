import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quotes", "0020_customer_quote_system"),
    ]

    operations = [
        # 1. Create the SalesRep table
        migrations.CreateModel(
            name="SalesRep",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
            ],
            options={"ordering": ["name"]},
        ),

        # 2. Remove the old User FK on CustomerQuote
        migrations.RemoveField(
            model_name="customerquote",
            field_name="rep",
        ),

        # 3. Add new SalesRep FK on CustomerQuote
        migrations.AddField(
            model_name="customerquote",
            name="rep",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="customer_quotes",
                to="quotes.salesrep",
            ),
        ),
    ]
