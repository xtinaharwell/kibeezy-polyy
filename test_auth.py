#!/usr/bin/env python
"""Test authentication flow"""
import os
import sys
import django

# Add the project directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from django.contrib.auth import authenticate
from users.models import CustomUser

# Test user
PHONE = "254712345678"
PIN = "1234"

print("\n=== AUTHENTICATION TEST ===\n")

# First, try to get the user directly
try:
    user = CustomUser.objects.get(phone_number=PHONE)
    print(f"✓ User found: {user.phone_number} ({user.full_name})")
except CustomUser.DoesNotExist:
    print(f"✗ User not found: {PHONE}")
    print("Creating test user...")
    user = CustomUser.objects.create_user(
        phone_number=PHONE,
        full_name="Test User",
        pin=PIN
    )
    print(f"✓ Created test user: {user.phone_number}")

# Test password check
print(f"\n✓ Password check: {user.check_password(PIN)}")

# Test authentication backend
print("\nTesting authentication backend...")
from users.backends import PhoneNumberBackend
backend = PhoneNumberBackend()
auth_user = backend.authenticate(None, phone_number=PHONE, password=PIN)
if auth_user:
    print(f"✓ Backend authenticate worked: {auth_user.phone_number}")
else:
    print(f"✗ Backend authenticate failed")

# Test Django's authenticate function
print("\nTesting Django authenticate function...")
from django.contrib.auth import authenticate
django_user = authenticate(phone_number=PHONE, password=PIN)
if django_user:
    print(f"✓ Django authenticate worked: {django_user.phone_number}")
else:
    print(f"✗ Django authenticate failed")
    print(f"  This might indicate the PhoneNumberBackend is not configured correctly")

print("\n=== END TEST ===\n")
