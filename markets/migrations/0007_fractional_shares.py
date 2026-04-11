# Generated migration for fractional shares support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('markets', '0006_bet_action'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bet',
            name='quantity',
            field=models.DecimalField(
                decimal_places=8,
                default=1,
                max_digits=15,
                help_text='Supports fractional shares (e.g., 19.6 shares)'
            ),
        ),
    ]
