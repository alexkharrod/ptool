from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='scouting_only',
            field=models.BooleanField(default=False, help_text='Restrict user to scouting section only'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='must_change_password',
            field=models.BooleanField(default=False, help_text='Force password change on next login'),
        ),
    ]
