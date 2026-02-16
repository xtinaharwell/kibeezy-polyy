# API Testing Guide

## Quick Start

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# For development/testing, set:
MPESA_DEBUG=True
DEBUG=True

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver
```

### 2. Test User Account
```bash
# Use phone number: 254712345678 (test number)
# PIN: 1234
# Full Name: Test User
```

---

## Test Scenarios

### Scenario 1: User Signup & Login

**Step 1: Signup**
```bash
curl -X POST http://localhost:8000/api/users/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "phone_number": "254712345678",
    "pin": "1234"
  }'
```

Expected Response:
```json
{
  "message": "Account created successfully",
  "user": {
    "phone_number": "254712345678",
    "full_name": "John Doe",
    "id": 1
  }
}
```

**Step 2: Login**
```bash
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "254712345678",
    "pin": "1234"
  }' \
  -c cookies.txt  # Save session cookie
```

Expected Response:
```json
{
  "message": "Login successful",
  "user": {
    "phone_number": "254712345678",
    "full_name": "John Doe",
    "id": 1,
    "kyc_verified": false
  },
  "csrf_token": "..."
}
```

**Step 3: Check Auth Status**
```bash
curl -X GET http://localhost:8000/api/users/check/ \
  -b cookies.txt  # Use session cookie
```

Expected Response:
```json
{
  "authenticated": true,
  "user": {
    "phone_number": "254712345678",
    "full_name": "John Doe",
    "id": 1,
    "balance": "0.00",
    "kyc_verified": false
  }
}
```

---

### Scenario 2: KYC Verification

**Step 1: Start KYC**
```bash
curl -X POST http://localhost:8000/api/users/kyc/start/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{}'
```

Expected Response (Development):
```json
{
  "message": "OTP sent to your phone number",
  "expires_in": 600,
  "otp_test_only": "123456"
}
```

**Step 2: Verify OTP**
```bash
curl -X POST http://localhost:8000/api/users/kyc/verify/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"otp": "123456"}'  # Use otp from step 1
```

Expected Response:
```json
{
  "message": "Phone number verified successfully",
  "kyc_verified": true,
  "user": {
    "id": 1,
    "phone_number": "254712345678",
    "kyc_verified": true
  }
}
```

**Step 3: Check KYC Status**
```bash
curl -X GET http://localhost:8000/api/users/kyc/status/ \
  -b cookies.txt
```

Expected Response:
```json
{
  "kyc_verified": true,
  "phone_number": "254712345678",
  "verified_at": "2024-01-15T10:30:45Z",
  "can_trade": true,
  "can_deposit": true
}
```

---

### Scenario 3: M-Pesa Deposit

**Prerequisite**: User must be KYC verified

**Step 1: Initiate STK Push**
```bash
curl -X POST http://localhost:8000/api/payments/initiate_stk_push/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"amount": 1000}'
```

Expected Response (Mock):
```json
{
  "message": "STK Push initiated successfully",
  "checkout_id": "ws_CO_04250223_test123",
  "transaction_id": 1,
  "customer_message": "Check your phone for M-Pesa prompt"
}
```

**Step 2: Simulate M-Pesa Callback** (for testing)
```bash
curl -X POST http://localhost:8000/api/payments/mpesa_callback/ \
  -H "Content-Type: application/json" \
  -d '{
    "Body": {
      "stkCallback": {
        "MerchantRequestID": "merchant_request_id",
        "CheckoutRequestID": "ws_CO_04250223_test123",
        "ResultCode": 0,
        "ResultDesc": "The service request has been processed successfully.",
        "CallbackMetadata": {
          "Item": [
            {"Name": "Amount", "Value": 1000},
            {"Name": "MpesaReceiptNumber", "Value": "LHG2K1Z9Z0"},
            {"Name": "TransactionDate", "Value": 20240115103000},
            {"Name": "PhoneNumber", "Value": 254712345678}
          ]
        }
      }
    }
  }'
```

**Step 3: Verify Balance Updated**
```bash
curl -X GET http://localhost:8000/api/users/check/ \
  -b cookies.txt
```

Expected Response:
```json
{
  "authenticated": true,
  "user": {
    "balance": "1000.00",  # Updated!
    ...
  }
}
```

---

### Scenario 4: Create Market (Admin)

**Prerequisite**: User must be admin (is_staff=True)

**Create Admin User** (one time setup):
```bash
python manage.py createsuperuser
# username/phone: 254722000001
# pin: 1234
```

**Step 1: Login as Admin**
```bash
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "254722000001",
    "pin": "1234"
  }' \
  -c admin_cookies.txt
```

**Step 2: Create Market**
```bash
curl -X POST http://localhost:8000/api/markets/create_market/ \
  -H "Content-Type: application/json" \
  -b admin_cookies.txt \
  -d '{
    "question": "Will Bitcoin reach $100,000 by end of 2024?",
    "category": "Technology",
    "description": "This market resolves to Yes if BTC price >= $100k",
    "end_date": "2024-12-31T23:59:59Z"
  }'
```

Expected Response:
```json
{
  "message": "Market created successfully",
  "market": {
    "id": 1,
    "question": "Will Bitcoin reach $100,000 by end of 2024?",
    "category": "Technology",
    "status": "OPEN",
    "end_date": "2024-12-31T23:59:59Z",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

### Scenario 5: Place Bet

**Prerequisite**: User must have balance and KYC verified

**Step 1: Place Bet**
```bash
curl -X POST http://localhost:8000/api/markets/place_bet/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "market_id": 1,
    "outcome": "Yes",
    "amount": 100
  }'
```

Expected Response:
```json
{
  "message": "Bet placed successfully",
  "bet_id": 1,
  "new_balance": "900.00"
}
```

---

### Scenario 6: Resolve Market (Admin)

**Prerequisite**: Admin must be logged in

**Step 1: Resolve Market**
```bash
curl -X POST http://localhost:8000/api/markets/resolve_market/ \
  -H "Content-Type: application/json" \
  -b admin_cookies.txt \
  -d '{
    "market_id": 1,
    "outcome": "Yes"
  }'
```

Expected Response:
```json
{
  "message": "Market resolved successfully",
  "market_id": 1,
  "outcome": "Yes",
  "payouts": {
    "total_wagered": "5000.00",
    "platform_fee": "500.00",
    "winners": 25,
    "losers": 75,
    "payout_per_winner": "180.00",
    "transactions_created": 100,
    "users_updated": 25
  }
}
```

**Step 2: Verify Payout**
```bash
curl -X GET http://localhost:8000/api/users/check/ \
  -b cookies.txt  # Original user who bet "Yes"
```

Expected Response:
```json
{
  "authenticated": true,
  "user": {
    "balance": "1080.00",  # Original 900 + payout 180
    ...
  }
}
```

---

### Scenario 7: Error Handling

**Invalid Phone Number**
```bash
curl -X POST http://localhost:8000/api/users/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "phone_number": "123",
    "pin": "1234"
  }'
```

Response:
```json
{
  "error": "Phone number must be in format 254xxxxxxxxx or 0xxxxxxxxx"
}
```

**Invalid PIN**
```bash
curl -X POST http://localhost:8000/api/users/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "phone_number": "254712345678",
    "pin": "12"
  }'
```

Response:
```json
{
  "error": "PIN must be exactly 4 digits"
}
```

**Insufficient Balance**
```bash
curl -X POST http://localhost:8000/api/markets/place_bet/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "market_id": 1,
    "outcome": "Yes",
    "amount": 999999
  }'
```

Response:
```json
{
  "error": "Insufficient balance. Available: KSH 100.00"
}
```

**KYC Not Verified**
```bash
curl -X POST http://localhost:8000/api/payments/initiate_stk_push/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"amount": 1000}'
```

Response (user not KYC verified):
```json
{
  "error": "KYC verification required",
  "message": "Please verify your phone number before making deposits"
}
```

---

## Postman Collection

Save as `kibeezy.postman_collection.json`:

```json
{
  "info": {
    "name": "Kibeezy API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Users",
      "item": [
        {
          "name": "Signup",
          "request": {
            "method": "POST",
            "url": "{{base_url}}/api/users/signup/",
            "body": {
              "raw": "{\"full_name\": \"John Doe\", \"phone_number\": \"254712345678\", \"pin\": \"1234\"}"
            }
          }
        },
        {
          "name": "Login",
          "request": {
            "method": "POST",
            "url": "{{base_url}}/api/users/login/",
            "body": {
              "raw": "{\"phone_number\": \"254712345678\", \"pin\": \"1234\"}"
            }
          }
        },
        {
          "name": "Check Auth",
          "request": {
            "method": "GET",
            "url": "{{base_url}}/api/users/check/"
          }
        }
      ]
    },
    {
      "name": "KYC",
      "item": [
        {
          "name": "Start KYC",
          "request": {
            "method": "POST",
            "url": "{{base_url}}/api/users/kyc/start/"
          }
        },
        {
          "name": "Verify KYC",
          "request": {
            "method": "POST",
            "url": "{{base_url}}/api/users/kyc/verify/",
            "body": {
              "raw": "{\"otp\": \"123456\"}"
            }
          }
        }
      ]
    },
    {
      "name": "Payments",
      "item": [
        {
          "name": "Initiate STK Push",
          "request": {
            "method": "POST",
            "url": "{{base_url}}/api/payments/initiate_stk_push/",
            "body": {
              "raw": "{\"amount\": 1000}"
            }
          }
        }
      ]
    },
    {
      "name": "Markets",
      "item": [
        {
          "name": "Create Market",
          "request": {
            "method": "POST",
            "url": "{{base_url}}/api/markets/create_market/",
            "body": {
              "raw": "{\"question\": \"Will X happen?\", \"category\": \"Technology\", \"end_date\": \"2024-12-31T23:59:59Z\"}"
            }
          }
        },
        {
          "name": "Place Bet",
          "request": {
            "method": "POST",
            "url": "{{base_url}}/api/markets/place_bet/",
            "body": {
              "raw": "{\"market_id\": 1, \"outcome\": \"Yes\", \"amount\": 100}"
            }
          }
        },
        {
          "name": "Resolve Market",
          "request": {
            "method": "POST",
            "url": "{{base_url}}/api/markets/resolve_market/",
            "body": {
              "raw": "{\"market_id\": 1, \"outcome\": \"Yes\"}"
            }
          }
        }
      ]
    }
  ],
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000/api",
      "type": "string"
    }
  ]
}
```

---

## Common Debugging

### Check Server is Running
```bash
curl -X GET http://localhost:8000/api/users/check/
```

### View Database
```bash
# Connect to SQLite (development)
sqlite3 db.sqlite3
SELECT * FROM users_customuser;

# Or PostgreSQL (production)
psql -U kibeezy_user -d kibeezy
SELECT * FROM users_customuser;
```

### View Logs
```bash
# Check Django logs (if configured)
tail -f logs/django.log

# Or in terminal if running with python manage.py runserver
# Logs appear directly in terminal output
```

### Reset Database (WARNING: Deletes all data)
```bash
python manage.py flush --no-input
python manage.py migrate
```

### Testing with Docker
```bash
# Run tests in container
docker-compose exec django python manage.py test

# Access shell in container
docker-compose exec django python manage.py shell
```

---

## Performance Testing

### Load Test with Locust
```bash
# Install locust
pip install locust

# Create locustfile.py
# (See deployment guide for example)

# Run load test
locust -f locustfile.py --host=http://localhost:8000
```

### Test with Apache Bench
```bash
# Install ab (Apache Bench)
# On Mac: brew install httpd (includes ab utility)
# On Linux: sudo apt-get install apache2-utils

# Load test an endpoint
ab -n 1000 -c 100 http://localhost:8000/api/users/check/
```

---

## Next Steps

1. **Run all test scenarios** to verify functionality
2. **Load test** with ab or locust
3. **Monitor database** for slow queries
4. **Check logs** for errors or warnings
5. **Document API** with Swagger/OpenAPI

Everything should be working! 🎉
