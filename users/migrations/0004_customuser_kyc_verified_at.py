from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_customuser_balance_customuser_kyc_verified'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='kyc_verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
