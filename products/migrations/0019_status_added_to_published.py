from django.db import migrations


def added_to_published(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    Product.objects.filter(status="Added").update(status="Published")


def published_to_added(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    Product.objects.filter(status="Published").update(status="Added")


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0018_website_content"),
    ]

    operations = [
        migrations.RunPython(added_to_published, reverse_code=published_to_added),
    ]
