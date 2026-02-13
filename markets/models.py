from django.db import models
from django.conf import settings

class Market(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
        ('RESOLVED', 'Resolved'),
    ]
    
    CATEGORY_CHOICES = [
        ('Sports', 'Sports'),
        ('Politics', 'Politics'),
        ('Economy', 'Economy'),
        ('Crypto', 'Crypto'),
        ('Environment', 'Environment'),
    ]

    question = models.CharField(max_length=500)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True, null=True)
    image_url = models.URLField(max_length=1000, blank=True, null=True)
    yes_probability = models.IntegerField(default=50)
    volume = models.CharField(max_length=100, default="KSh 0")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    end_date = models.CharField(max_length=100)
    resolved_outcome = models.CharField(max_length=10, choices=[('Yes', 'Yes'), ('No', 'No')], null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_markets')
    is_live = models.BooleanField(default=True)  # Kept for backward compatibility

    def __str__(self):
        return self.question

class Bet(models.Model):
    RESULT_CHOICES = [
        ('PENDING', 'Pending'),
        ('WON', 'Won'),
        ('LOST', 'Lost'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bets')
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='bets')
    outcome = models.CharField(max_length=10, choices=[('Yes', 'Yes'), ('No', 'No')])
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    entry_probability = models.IntegerField(default=50)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default='PENDING')
    payout = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.phone_number} - {self.market.question} - {self.outcome}"

    def __str__(self):
        return f"{self.user.phone_number} - {self.market.question} - {self.outcome}"
