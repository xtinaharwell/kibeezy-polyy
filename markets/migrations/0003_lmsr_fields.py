"""
Migration for LMSR model updates.
Adds q_yes, q_no, b, and trading_end_time fields for LMSR implementation.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('markets', '0002_auto_previous_migration'),  # Update to actual previous migration name
    ]

    operations = [
        # Add LMSR fields
        migrations.AddField(
            model_name='market',
            name='q_yes',
            field=models.FloatField(default=0.0, help_text='LMSR YES quantity scalar'),
        ),
        migrations.AddField(
            model_name='market',
            name='q_no',
            field=models.FloatField(default=0.0, help_text='LMSR NO quantity scalar'),
        ),
        migrations.AddField(
            model_name='market',
            name='b',
            field=models.FloatField(default=100.0, help_text='LMSR liquidity parameter'),
        ),
        migrations.AddField(
            model_name='market',
            name='trading_end_time',
            field=models.DateTimeField(blank=True, null=True, help_text='When trading closes for this market'),
        ),
    ]
