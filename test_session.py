#!/usr/bin/env python
"""Test session-based authentication flow"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("\n=== SESSION-BASED AUTHENTICATION TEST ===\n")

# Create a session to maintain cookies
session = requests.Session()

# Test user credentials
PHONE = "254712345678"
PIN = "1234"

# Step 1: Test login
print("1. Testing login endpoint...")
login_response = session.post(
    f"{BASE_URL}/api/auth/login/",
    json={"phone_number": PHONE, "pin": PIN},
    headers={"Content-Type": "application/json"}
)

print(f"   Status: {login_response.status_code}")
login_data = login_response.json()
print(f"   Response: {login_data.get('message', login_data.get('error', login_data))}")

if login_response.status_code == 200:
    print(f"   ✓ Login successful")
else:
    print(f"   ✗ Login failed")

# Check cookies
print(f"\n2. Checking cookies after login...")
print(f"   Session cookies: {session.cookies}")
for cookie in session.cookies:
    print(f"    - {cookie.name}: {cookie.value[:20]}...")

# Step 2: Test auth check endpoint
print(f"\n3. Testing /auth/check/ endpoint (should be authenticated)...")
check_response = session.get(
    f"{BASE_URL}/api/auth/check/",
    headers={"Content-Type": "application/json"}
)

print(f"   Status: {check_response.status_code}")
check_data = check_response.json()
print(f"   Authenticated: {check_data.get('authenticated')}")

if check_data.get('authenticated'):
    print(f"   ✓ Session maintained - user is authenticated")
    print(f"   ✓ User: {check_data.get('user')}")
else:
    print(f"   ✗ Session not maintained")
    print(f"   Debug info: {check_data}")

print("\n=== END TEST ===\n")
