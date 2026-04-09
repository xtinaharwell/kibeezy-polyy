# Generated migration for adding phone_locked field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_customuser_email_customuser_google_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='phone_locked',
            field=models.BooleanField(default=False, help_text='Locked after first confirmed deposit to prevent fraud'),
        ),
    ]
