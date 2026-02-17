# Generated migration for Notification model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('WELCOME', 'Welcome'), ('ACCOUNT_VERIFIED', 'Account Verified'), ('DEPOSIT_CONFIRMED', 'Deposit Confirmed'), ('DEPOSIT_FAILED', 'Deposit Failed'), ('WITHDRAWAL_CONFIRMED', 'Withdrawal Confirmed'), ('WITHDRAWAL_FAILED', 'Withdrawal Failed'), ('BET_PLACED', 'Bet Placed'), ('BET_WON', 'Bet Won'), ('BET_LOST', 'Bet Lost'), ('MARKET_RESOLVED', 'Market Resolved'), ('NEW_MARKET', 'New Market Available'), ('PAYOUT_PROCESSED', 'Payout Processed'), ('KYC_REQUIRED', 'KYC Required'), ('KYC_APPROVED', 'KYC Approved'), ('KYC_REJECTED', 'KYC Rejected'), ('SYSTEM_MESSAGE', 'System Message')], max_length=20)),
                ('title', models.CharField(max_length=150)),
                ('message', models.TextField()),
                ('color_class', models.CharField(default='blue', help_text='Color scheme: blue, green, purple, orange, red', max_length=20)),
                ('related_market_id', models.IntegerField(blank=True, null=True)),
                ('related_transaction_id', models.IntegerField(blank=True, null=True)),
                ('related_bet_id', models.IntegerField(blank=True, null=True)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['user', '-created_at'], name='notification_user_id_created_idx'),
                    models.Index(fields=['user', 'is_read'], name='notification_user_id_is_read_idx'),
                ],
            },
        ),
    ]
