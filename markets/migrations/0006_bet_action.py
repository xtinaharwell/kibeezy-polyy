# Generated migration for action field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('markets', '0005_bet_limit_and_quantity'),
    ]

    operations = [
        migrations.AddField(
            model_name='bet',
            name='action',
            field=models.CharField(
                choices=[('BUY', 'Buy'), ('SELL', 'Sell')],
                default='BUY',
                max_length=10,
            ),
        ),
    ]
