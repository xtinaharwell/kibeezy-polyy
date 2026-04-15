# Generated migration to support fractional shares with 8 decimal places

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('markets', '0014_remove_market_is_bootstrapped_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bet',
            name='amount',
            field=models.DecimalField(decimal_places=8, max_digits=15),
        ),
    ]
