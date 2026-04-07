from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0017_imprintmethod"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="website_description",
            field=models.TextField(
                blank=True,
                help_text="AI-generated HTML description for the website (replaces specs on NPDS).",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="website_keywords",
            field=models.TextField(
                blank=True,
                help_text="Comma-separated keyword phrases for product search (up to 30).",
            ),
        ),
    ]
