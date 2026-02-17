#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from users.models import CustomUser
from decimal import Decimal

# Update user balance
phone_number = '0718693484'
try:
    user = CustomUser.objects.get(phone_number=phone_number)
    user.balance = Decimal('15000.00')
    user.save()
    print(f"✅ Successfully updated balance for {phone_number}")
    print(f"   New balance: KSh {user.balance}")
except CustomUser.DoesNotExist:
    print(f"❌ User with phone number {phone_number} not found")
except Exception as e:
    print(f"❌ Error: {e}")
