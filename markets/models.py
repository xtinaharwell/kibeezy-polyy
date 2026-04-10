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

    MARKET_TYPE_CHOICES = [
        ('BINARY', 'Binary'),
        ('OPTION_LIST', 'Option List'),
    ]

    question = models.CharField(max_length=500)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True, null=True)
    image_url = models.URLField(max_length=1000, blank=True, null=True)
    market_type = models.CharField(max_length=20, choices=MARKET_TYPE_CHOICES, default='BINARY')
    yes_probability = models.IntegerField(default=50)  # For BINARY markets
    options = models.JSONField(null=True, blank=True)  # For OPTION_LIST markets: [{"id": 1, "label": "...", "yes_probability": 50}, ...]
    volume = models.CharField(max_length=100, default="KES 0")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    end_date = models.CharField(max_length=100)
    resolved_outcome = models.CharField(max_length=10, choices=[('Yes', 'Yes'), ('No', 'No')], null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_markets')
    is_live = models.BooleanField(default=True)  # Kept for backward compatibility
    
    # AMM (Automated Market Maker) fields
    yes_reserve = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # YES share reserve in KES value
    no_reserve = models.DecimalField(max_digits=15, decimal_places=2, default=0)   # NO share reserve in KES value
    is_bootstrapped = models.BooleanField(default=False)  # Track if initial liquidity was added

    def __str__(self):
        return self.question

class Bet(models.Model):
    RESULT_CHOICES = [
        ('PENDING', 'Pending'),
        ('WON', 'Won'),
        ('LOST', 'Lost'),
    ]
    
    ACTION_CHOICES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bets')
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='bets')
    outcome = models.CharField(max_length=10, choices=[('Yes', 'Yes'), ('No', 'No')])
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    entry_probability = models.IntegerField(default=50)
    option_id = models.IntegerField(null=True, blank=True)  # For OPTION_LIST markets: identifies which option was traded
    option_label = models.CharField(max_length=255, null=True, blank=True)  # Denormalized for quick lookup
    ORDER_TYPE_CHOICES = [
        ('MARKET', 'Market'),
        ('LIMIT', 'Limit'),
    ]
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES, default='MARKET')
    limit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default='PENDING')
    payout = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, default='BUY')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.phone_number} - {self.market.question} - {self.outcome}"


class PriceHistory(models.Model):
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='price_history')
    option_id = models.IntegerField(null=True, blank=True)  # For OPTION_LIST markets
    yes_probability = models.IntegerField()
    no_probability = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['market', 'option_id', 'timestamp']),
        ]
    
    def __str__(self):
        option_str = f" Option {self.option_id}" if self.option_id else ""
        return f"{self.market.id}{option_str} - Yes: {self.yes_probability}% at {self.timestamp}"


class ChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_messages')
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='chat_messages')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.parent:
            return f"{self.user.phone_number} replied to {self.parent.user.phone_number} on {self.market.id}: {self.message[:40]}"
        return f"{self.user.phone_number} on {self.market.id}: {self.message[:40]}"
