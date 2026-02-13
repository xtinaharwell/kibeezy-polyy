#!/usr/bin/env python
"""Simulate the browser flow: login -> check auth -> make bet"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("\n=== COMPLETE AUTH FLOW TEST (Browser Simulation) ===\n")

# Create a session to maintain cookies (simulating browser cookie jar)
session = requests.Session()

# Set the origin header to simulate browser
session.headers.update({
    "Origin": "http://127.0.0.1:3000",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
})

PHONE = "254712345678"
PIN = "1234"

# Step 1: Login
print("1. LOGIN")
print("=" * 50)
login_resp = session.post(
    f"{BASE_URL}/api/auth/login/",
    json={"phone_number": PHONE, "pin": PIN}
)
print(f"Status: {login_resp.status_code}")
print(f"Response: {login_resp.json().get('message', login_resp.json().get('error'))}")
print(f"Cookies in session: {dict(session.cookies)}")

# Step 2: Check auth immediately
print("\n2. AUTH CHECK (right after login)")
print("=" * 50)
check1 = session.get(f"{BASE_URL}/api/auth/check/")
print(f"Status: {check1.status_code}")
print(f"Authenticated: {check1.json().get('authenticated')}")

# Step 3: Try STK push
print("\n3. STK PUSH REQUEST")
print("=" * 50)
stk_resp = session.post(
    f"{BASE_URL}/api/payments/stk-push/",
    json={"amount": 1000}
)
print(f"Status: {stk_resp.status_code}")
print(f"Response: {stk_resp.json()}")

# Step 4: Try place bet
print("\n4. PLACE BET REQUEST")
print("=" * 50)
bet_resp = session.post(
    f"{BASE_URL}/api/markets/bet/",
    json={"market_id": 1, "outcome": "Yes", "amount": 500}
)
print(f"Status: {bet_resp.status_code}")
print(f"Response: {bet_resp.json()}")

print("\n=== END TEST ===\n")
