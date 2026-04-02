from django.db import migrations, models
from django.db.migrations.operations.special import SeparateDatabaseAndState


class Migration(migrations.Migration):

    dependencies = [
        ('markets', '0004_chatmessage_parent'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=[
                        "ALTER TABLE markets_bet ADD COLUMN IF NOT EXISTS order_type character varying(10) NOT NULL DEFAULT 'MARKET';",
                        "ALTER TABLE markets_bet ADD COLUMN IF NOT EXISTS limit_price numeric(12,2);",
                        "ALTER TABLE markets_bet ADD COLUMN IF NOT EXISTS quantity integer NOT NULL DEFAULT 1;",
                    ],
                    reverse_sql=[
                        "ALTER TABLE markets_bet DROP COLUMN IF EXISTS order_type;",
                        "ALTER TABLE markets_bet DROP COLUMN IF EXISTS limit_price;",
                        "ALTER TABLE markets_bet DROP COLUMN IF EXISTS quantity;",
                    ],
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='bet',
                    name='order_type',
                    field=models.CharField(choices=[('MARKET', 'Market'), ('LIMIT', 'Limit')], default='MARKET', max_length=10),
                ),
                migrations.AddField(
                    model_name='bet',
                    name='limit_price',
                    field=models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True),
                ),
                migrations.AddField(
                    model_name='bet',
                    name='quantity',
                    field=models.PositiveIntegerField(default=1),
                ),
            ],
        ),
    ]
