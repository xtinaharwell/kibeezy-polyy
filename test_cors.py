#!/usr/bin/env python
"""Test CORS headers and fetch-style requests"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("\n=== CORS HEADERS CHECK ===\n")

# Simulate a fetch request from http://127.0.0.1:3000
headers = {
    "Origin": "http://127.0.0.1:3000",
    "Content-Type": "application/json",
}

print("1. Login request with CORS origin header...")
response = requests.post(
    f"{BASE_URL}/api/auth/login/",
    json={"phone_number": "254712345678", "pin": "1234"},
    headers=headers
)

print(f"   Status: {response.status_code}")
print(f"   Response headers:")
for header, value in response.headers.items():
    if 'access' in header.lower() or 'allow' in header.lower() or 'cookie' in header.lower():
        print(f"    - {header}: {value}")

print(f"\n   Set-Cookie headers:")
set_cookies = []
if 'Set-Cookie' in response.headers:
    # requests library combines multiple Set-Cookie headers into a single value
    set_cookie_header = response.headers.get('Set-Cookie', '')
    # Split by comma but be careful about dates
    parts = set_cookie_header.split(', ')
    for part in parts:
        if part.strip():
            set_cookies.append(part)
            print(f"    - {part}")
else:
    print(f"    - No Set-Cookie header found")

print(f"\n   Django response data: {response.json().get('message', response.json().get('error'))}")

# Now test with the extracted session cookie
print(f"\n2. Check auth with session cookie...")

# Extract sessionid from cookies
session_cookie = None
csrf_cookie = None

for cookie_str in set_cookies:
    if 'sessionid=' in cookie_str:
        session_cookie = cookie_str.split(';')[0]
    if 'csrftoken=' in cookie_str:
        csrf_cookie = cookie_str.split(';')[0]

if session_cookie:
    print(f"   Found sessionid: {session_cookie[:50]}...")
    
    # Now make a request with this cookie
    check_headers = {
        "Origin": "http://127.0.0.1:3000",
        "Content-Type": "application/json",
        "Cookie": f"{session_cookie}; {csrf_cookie}" if csrf_cookie else session_cookie
    }
    
    check_response = requests.get(
        f"{BASE_URL}/api/auth/check/",
        headers=check_headers
    )
    
    print(f"   Auth check status: {check_response.status_code}")
    check_data = check_response.json()
    print(f"   Authenticated: {check_data.get('authenticated')}")
    
    if check_data.get('authenticated'):
        print(f"   ✓ User is authenticated with session cookie")
    else:
        print(f"   ✗ Session cookie not working")
else:
    print(f"   ✗ No sessionid cookie found in response")

print("\n=== END TEST ===\n")
