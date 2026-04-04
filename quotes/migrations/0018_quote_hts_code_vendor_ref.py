from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0016_category'),
        ('quotes', '0017_quote_category_choices'),
    ]

    operations = [
        migrations.AddField(
            model_name='quote',
            name='hts_code',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='products.htscode',
            ),
        ),
        migrations.AddField(
            model_name='quote',
            name='vendor_ref',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='products.vendor',
            ),
        ),
    ]
