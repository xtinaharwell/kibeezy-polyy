from django.db import models
from django.conf import settings

class Notification(models.Model):
    TYPE_CHOICES = [
        ('WELCOME', 'Welcome'),
        ('ACCOUNT_VERIFIED', 'Account Verified'),
        ('DEPOSIT_CONFIRMED', 'Deposit Confirmed'),
        ('DEPOSIT_FAILED', 'Deposit Failed'),
        ('WITHDRAWAL_CONFIRMED', 'Withdrawal Confirmed'),
        ('WITHDRAWAL_FAILED', 'Withdrawal Failed'),
        ('BET_PLACED', 'Bet Placed'),
        ('BET_WON', 'Bet Won'),
        ('BET_LOST', 'Bet Lost'),
        ('MARKET_RESOLVED', 'Market Resolved'),
        ('NEW_MARKET', 'New Market Available'),
        ('PAYOUT_PROCESSED', 'Payout Processed'),
        ('KYC_REQUIRED', 'KYC Required'),
        ('KYC_APPROVED', 'KYC Approved'),
        ('KYC_REJECTED', 'KYC Rejected'),
        ('SYSTEM_MESSAGE', 'System Message'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=150)
    message = models.TextField()
    color_class = models.CharField(max_length=20, default='blue', help_text='Color scheme: blue, green, purple, orange, red')
    
    # Optional links
    related_market_id = models.IntegerField(null=True, blank=True)
    related_transaction_id = models.IntegerField(null=True, blank=True)
    related_bet_id = models.IntegerField(null=True, blank=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.user.phone_number} - {self.type} - {self.title}"
