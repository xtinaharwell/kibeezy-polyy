# Generated migration for B2C fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='external_ref',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='transaction',
            name='mpesa_response',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
