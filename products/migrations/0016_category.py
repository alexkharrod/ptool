from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0015_product_category_choices'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10, unique=True)),
                ('description', models.CharField(max_length=100)),
            ],
            options={
                'verbose_name_plural': 'Categories',
                'ordering': ['code'],
            },
        ),
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
