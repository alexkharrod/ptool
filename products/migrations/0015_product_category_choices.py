from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0014_merge_0013_migrations'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.CharField(
                blank=True,
                max_length=10,
                choices=[
                    ('AC', 'AC Adapters'),
                    ('AT', 'Air Trackers'),
                    ('CB', 'Cables'),
                    ('CM', 'Custom Molds'),
                    ('DF', 'Digital Frames'),
                    ('DW', 'Drinkware'),
                    ('EB', 'Earbuds / Headphones'),
                    ('FN', 'Fans'),
                    ('FT', 'Fitness'),
                    ('HW', 'Hand Warmers'),
                    ('JB', 'Power Banks'),
                    ('LY', 'Lanyards'),
                    ('MA', 'Mobile Accessories'),
                    ('Misc', 'Miscellaneous'),
                    ('NFC', 'Near Field / RFID'),
                    ('OA', 'Office Accessories'),
                    ('RT', 'Retail'),
                    ('SC', 'Screen Cleaners'),
                    ('SL', 'Selfie Lights'),
                    ('SP', 'Speakers'),
                    ('ST', 'Straws'),
                    ('TA', 'Travel Adapters'),
                    ('TL', 'Tools'),
                    ('TT', 'Fidget Games'),
                    ('UD', 'USB Drives'),
                    ('UH', 'USB Hubs'),
                    ('WC', 'Wireless Chargers'),
                ],
            ),
        ),
    ]
