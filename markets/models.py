from django.db import models
from django.conf import settings

class Market(models.Model):
    CATEGORY_CHOICES = [
        ('Sports', 'Sports'),
        ('Politics', 'Politics'),
        ('Economy', 'Economy'),
        ('Crypto', 'Crypto'),
        ('Environment', 'Environment'),
    ]

    question = models.CharField(max_length=500)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    image_url = models.URLField(max_length=1000, blank=True, null=True)
    yes_probability = models.IntegerField(default=50)
    volume = models.CharField(max_length=100, default="$0")
    is_live = models.BooleanField(default=True)
    end_date = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question

class Bet(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='bets')
    outcome = models.CharField(max_length=10, choices=[('Yes', 'Yes'), ('No', 'No')])
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.phone_number} - {self.market.question} - {self.outcome}"
