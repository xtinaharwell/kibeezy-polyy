#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.settings")
django.setup()

from notifications.models import Notification
from users.models import CustomUser

# Get the user
try:
    user = CustomUser.objects.get(phone_number='0718693484')
except CustomUser.DoesNotExist:
    print("User with phone number 0718693484 not found")
    exit(1)

# Create three notifications of different types
notifications = [
    {
        'type': 'WELCOME',
        'title': 'Welcome to KASOKO!',
        'message': 'Start predicting markets to earn rewards',
        'color_class': 'blue'
    },
    {
        'type': 'DEPOSIT_CONFIRMED',
        'title': 'Deposit Confirmed',
        'message': 'Your deposit of KSh 5,000 has been confirmed',
        'color_class': 'green'
    },
    {
        'type': 'BET_PLACED',
        'title': 'Bet Placed Successfully',
        'message': 'Your prediction of Yes for KSh 2,000 has been placed on "Will Kenya lower interest rates by June?"',
        'color_class': 'purple'
    }
]

for notif_data in notifications:
    notification = Notification.objects.create(
        user=user,
        type=notif_data['type'],
        title=notif_data['title'],
        message=notif_data['message'],
        color_class=notif_data['color_class']
    )
    print(f"✅ Created notification: {notification.type} - {notification.title}")

print(f"\n✅ Successfully added {len(notifications)} notifications to user {user.phone_number}")
