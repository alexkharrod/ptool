from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quotes', '0016_quote_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='quote',
            name='category',
            field=models.CharField(
                blank=True,
                default='',
                max_length=50,
                choices=[
                    ('AC', 'AC – AC Adapters'),
                    ('AT', 'AT – Air Trackers'),
                    ('CB', 'CB – Cables'),
                    ('CM', 'CM – Custom Molds'),
                    ('DF', 'DF – Digital Frames'),
                    ('DW', 'DW – Drinkware'),
                    ('EB', 'EB – Earbuds / Headphones'),
                    ('FN', 'FN – Fans'),
                    ('FT', 'FT – Fitness'),
                    ('HW', 'HW – Hand Warmers'),
                    ('JB', 'JB – Power Banks'),
                    ('LY', 'LY – Lanyards'),
                    ('MA', 'MA – Mobile Accessories'),
                    ('MG', 'MG – Massage Guns'),
                    ('Misc', 'Misc – Miscellaneous'),
                    ('NFC', 'NFC – Near Field / RFID'),
                    ('OA', 'OA – Office Accessories'),
                    ('RT', 'RT – Retail'),
                    ('SC', 'SC – Screen Cleaners'),
                    ('SL', 'SL – Selfie Lights'),
                    ('SP', 'SP – Speakers'),
                    ('ST', 'ST – Straws'),
                    ('TA', 'TA – Travel Adapters'),
                    ('TL', 'TL – Tools'),
                    ('TT', 'TT – Fidget Games'),
                    ('UD', 'UD – USB Drives'),
                    ('UH', 'UH – USB Hubs'),
                    ('WC', 'WC – Wireless Chargers'),
                ],
            ),
        ),
    ]
