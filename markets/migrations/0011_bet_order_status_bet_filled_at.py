# Generated migration for order_status and filled_at fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('markets', '0010_market_is_bootstrapped_market_no_reserve_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bet',
            name='order_status',
            field=models.CharField(
                choices=[('PENDING', 'Pending'), ('FILLED', 'Filled'), ('CANCELLED', 'Cancelled'), ('EXPIRED', 'Expired')],
                default='FILLED',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='bet',
            name='filled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
