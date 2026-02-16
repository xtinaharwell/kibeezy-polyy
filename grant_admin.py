#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from users.models import CustomUser

# Grant admin privileges
phone_number = '0718693484'
try:
    user = CustomUser.objects.get(phone_number=phone_number)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f"✅ Successfully granted admin privileges to {phone_number}")
    print(f"   - is_staff: {user.is_staff}")
    print(f"   - is_superuser: {user.is_superuser}")
except CustomUser.DoesNotExist:
    print(f"❌ User with phone number {phone_number} not found")
except Exception as e:
    print(f"❌ Error: {e}")
