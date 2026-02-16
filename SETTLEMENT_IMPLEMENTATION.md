
# KASOKO Market Settlement & Payout System - Implementation Guide

## Overview
This guide covers the complete implementation of the pari-mutuel market settlement and M-Pesa B2C payout system for KASOKO prediction markets.

---

## Part 1: Architecture & Components

### 1.1 Settlement Flow
```
Market Closes
    ↓
Admin resolves outcome (POST /api/markets/admin/resolve/)
    ↓
Celery task: settle_market()
    - Lock market (atomic)
    - Calculate pari-mutuel payouts
    - Create payout Transaction records
    - Enqueue B2C calls
    ↓
Celery task: send_b2c_payout() (for each payout)
    - Get OAuth token from Daraja
    - Call B2C API
    - Store response metadata
    ↓
M-Pesa processes payment
    ↓
Daraja callback → POST /api/payments/b2c-callback/
    ↓
Django view: b2c_result_callback()
    - Verify callback
    - Mark transaction SUCCESS/FAILED
    - Credit user wallet
    ↓
User receives payout in wallet
```

### 1.2 Key Models
- **Market**: Contains question, status, resolved_outcome, platform_fee_pct
- **Bet**: Links user → market → outcome with amount + result + payout
- **Transaction**: Tracks deposits, withdrawals, payouts, and B2C metadata
- **CustomUser**: Has balance field for wallet management

---

## Part 2: Setup Instructions

### 2.1 Dependencies
Install the required packages:

```bash
pip install celery redis cryptography requests
```

Requirements.txt should include:
```
celery>=5.3
redis>=4.5
cryptography>=41.0
requests>=2.31
```

### 2.2 Redis Installation

**On Linux/Mac:**
```bash
brew install redis  # macOS
sudo apt-get install redis-server  # Ubuntu/Debian
redis-server  # Start server
```

**On Windows:**
- Download Redis from: https://github.com/microsoftarchive/redis/releases
- Or use WSL2 + Linux setup
- Or use Docker:

```bash
docker run -d -p 6379:6379 redis:latest
```

### 2.3 Environment Variables

Create/update your `.env` file with:

```env
# Redis
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1

# M-Pesa Daraja (Sandbox first, then production)
MPESA_PRODUCTION=False
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_INITIATOR_NAME=testapi
MPESA_SECURITY_CREDENTIAL_ENCRYPTED=your_encrypted_credential  # See section 2.5
MPESA_PAYBILL=600000
MPESA_CALLBACK_URL=https://kasoko.app/api/payments/b2c-callback/

# Payouts
PAYOUT_PLATFORM_FEE_PCT=5.00
PAYOUT_MIN_AMOUNT=10

# Celery
CELERY_WORKER_CONCURRENCY=4
```

### 2.4 M-Pesa Daraja Setup

1. **Register on Daraja**: https://developer.safaricom.co.ke/
2. **Create an app** in the Daraja console
3. **Get credentials**:
   - Consumer Key
   - Consumer Secret
   - Cache OAuth tokens (valid 1 hour)

4. **For B2C payouts**, you need:
   - A registered **Initiator** (user at Safaricom)
   - **Security Credential**: Initiator password encrypted with Safaricom public cert
   - **Paybill/Shortcode**: Your business till number

### 2.5 Security Credential Encryption

The initiator password must be encrypted using Safaricom's public certificate.

1. Download the Safaricom public cert from Daraja (provided as `.pem` file)
2. Encrypt your initiator password:

```python
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64

# Read Safaricom cert
with open('path/to/safaricom_cert.pem', 'rb') as f:
    public_key = serialization.load_pem_public_key(f.read(), default_backend())

# Encrypt password
initiator_password = "your_initiator_password"
encrypted = public_key.encrypt(
    initiator_password.encode(),
    padding.PKCS1v15()
)

# Base64 encode for env variable
encrypted_b64 = base64.b64encode(encrypted).decode()
print(encrypted_b64)  # Store this in MPESA_SECURITY_CREDENTIAL_ENCRYPTED
```

### 2.6 Update URLs

Add routes to `markets/urls.py` for admin settlement endpoints:

```python
from markets.admin_settlement_views import (
    resolve_market, settlement_status, retry_payout,
    retry_failed_payouts_batch
)

urlpatterns = [
    # ... existing patterns ...
    path('admin/resolve/', resolve_market, name='resolve_market'),
    path('admin/settlement-status/<int:market_id>/', settlement_status, name='settlement_status'),
    path('admin/retry-payout/', retry_payout, name='retry_payout'),
    path('admin/retry-failed-payouts/', retry_failed_payouts_batch, name='retry_failed_payouts'),
]
```

---

## Part 3: Running the System

### 3.1 Start Redis
```bash
redis-server
# or with docker
docker run -d -p 6379:6379 redis:latest
```

### 3.2 Start Celery Worker

Open a new terminal and run:

```bash
cd kibeezy-polyy
celery -A api worker -l info --concurrency=4
```

For development with auto-reload:
```bash
celery -A api worker -l info --concurrency=1 -B
```

The `-B` flag also starts Celery Beat (scheduler) for periodic tasks.

### 3.3 Run Django Dev Server

```bash
python manage.py runserver
```

### 3.4 Check Celery Status (Flower - optional UI)

```bash
pip install flower
celery -A api events --loglevel=info
celery -A api flower
# Visit http://localhost:5555
```

---

## Part 4: Testing the Flow

### 4.1 Create Test Data

```python
# Django shell: python manage.py shell

from markets.models import Market, Bet, Outcome
from users.models import CustomUser
from decimal import Decimal

# Create users
user1 = CustomUser.objects.create_user(phone_number='254712345678', full_name='User 1', pin='1234')
user2 = CustomUser.objects.create_user(phone_number='254712345679', full_name='User 2', pin='1234')

# Give them balance
user1.balance = Decimal('1000')
user1.save()
user2.balance = Decimal('2000')
user2.save()

# Create market
market = Market.objects.create(
    question="Will it rain tomorrow?",
    category="Environment",
    status="OPEN",
    end_date="2026-02-17"
)

# Create bets
bet1 = Bet.objects.create(
    user=user1, market=market, outcome="Yes", amount=100
)
bet2 = Bet.objects.create(
    user=user2, market=market, outcome="No", amount=200
)

print(f"Market {market.id} created with 2 bets")
print(f"Total pool: {Decimal('100') + Decimal('200')}")
```

### 4.2 Resolve Market & Trigger Settlement

```bash
# Via API
curl -X POST http://127.0.0.1:8000/api/markets/admin/resolve/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer yourtoken" \
  -d '{
    "market_id": 1,
    "outcome": "Yes"
  }'
```

Response:
```json
{
  "status": "resolved",
  "market_id": 1,
  "outcome": "Yes",
  "settlement_task_id": "abc123-task-id"
}
```

### 4.3 Monitor in Celery

Watch the worker terminal—you should see:
```
[2026-02-16 10:30:45,123: INFO/MainProcess] Task payments.settlement_tasks.settle_market[task-id] received
[2026-02-16 10:30:46,456: INFO/MainProcess] Settling market 1: total_pool=300, ...
[2026-02-16 10:30:47,789: INFO/MainProcess] Task payments.settlement_tasks.send_b2c_payout[task-id] received
[2026-02-16 10:30:49,012: INFO/MainProcess] Initiating B2C payout for transaction 1, amount=150
```

### 4.4 Simulate B2C Callback (Sandbox)

In sandbox, Daraja may provide a tool to send test callbacks. Alternatively, manually POST:

```bash
curl -X POST http://127.0.0.1:8000/api/payments/b2c-callback/ \
  -H "Content-Type: application/json" \
  -d '{
    "Result": {
      "ResultCode": 0,
      "ResultDesc": "The service request has been processed successfully.",
      "OriginatorConversationID": "...",
      "ConversationID": "...",
      "ExternalReference": "KASOKO-1-1-1613398249.5",
      "ResponseDescription": "success"
    }
  }'
```

Expect 200 OK response and payout transaction marked COMPLETED.

---

## Part 5: Database Migrations

After updates to `models.py` (if needed), run:

```bash
python manage.py makemigrations
python manage.py migrate
```

Ensure Transaction model has `external_ref` field (unique).

---

## Part 6: Production Checklist

### Pre-Launch
- [ ] Update settings: `DEBUG=False`, `MPESA_PRODUCTION=True`
- [ ] Move M-Pesa credentials to secure vault (AWS Secrets Manager, Hashicorp Vault, etc.)
- [ ] Configure HTTPS for callback URL
- [ ] Set up monitoring/alerting (Sentry, DataDog, New Relic)
- [ ] Test full settlement flow in Daraja sandbox
- [ ] Load test: 100+ concurrent settlements
- [ ] Set up daily reconciliation job (Daraja ↔ local DB)
- [ ] Configure backup strategy for Redis and PostgreSQL
- [ ] Security audit: inspect callback validation, API auth, CORS

### Post-Launch
- [ ] Monitor payout success rate (target: >99%)
- [ ] Review failed payout logs weekly
- [ ] Implement admin dashboard for manual payout recovery
- [ ] Set up alerts for failed payouts > threshold
- [ ] Daily balance reconciliation
- [ ] Monthly audit trail review

---

## Part 7: Common Errors & Fixes

### Error: Redis Connection Refused
```
Error: ConnectionError: Error 111 connecting to 127.0.0.1:6379. Connection refused.
```
**Fix**: Start Redis: `redis-server` or `docker run -p 6379:6379 redis:latest`

### Error: Celery Task Never Executes
```
Task received but state stays PENDING
```
**Fix**: Ensure Celery worker is running: `celery -A api worker -l info`

### Error: B2C Call Returns 401 Unauthorized
```
Response: {"error": "invalid credentials"}
```
**Fix**: 
- Verify CONSUMER_KEY/CONSUMER_SECRET in Daraja console
- Check token expiry (1 hour)—implement token caching if needed
- Ensure you're using sandbox URL for sandbox credentials

### Error: Callback Not Received
```
Payout stuck in PENDING status
```
**Fix**:
- Verify callback URL is HTTPS and publicly accessible
- Check Django logs for POST to `/api/payments/b2c-callback/`
- Ensure firewall allows inbound HTTPS
- Test callback manually (see section 4.4)

### Error: Decimal Precision Loss
```
Payout amount rounds incorrectly
```
**Fix**: Always use `Decimal` type for financial calculations, never float

---

## Part 8: Sample Admin Dashboard API

Example admin panel calls:

```bash
# Check settlement status
curl http://127.0.0.1:8000/api/markets/admin/settlement-status/1/ \
  -H "Authorization: Bearer token"

# Manually retry failed payout
curl -X POST http://127.0.0.1:8000/api/payments/admin/retry-payout/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer token" \
  -d '{"transaction_id": 42}'

# Batch retry all failed payouts in past 24h
curl -X POST http://127.0.0.1:8000/api/payments/admin/retry-failed-payouts/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer token" \
  -d '{"hours": 24}'
```

---

## Part 9: Next Steps

1. **Integrate KYC verification**: Add progressive KYC for withdrawal limits
2. **Notifications**: Send SMS/push to users when payouts complete
3. **Cashout flow**: Let users withdraw from wallet via M-Pesa STK Push
4. **Recurring payouts**: Use Celery Beat for scheduled settlement checks
5. **Dispute resolution**: Admin interface to handle payout disputes
6. **Audit logging**: Log all settlement operations for regulatory compliance

---

## Support & References

- **Daraja API Docs**: https://developer.safaricom.co.ke/
- **Celery Docs**: https://docs.celeryproject.org/
- **Redis Docs**: https://redis.io/documentation
- **Django Celery**: https://docs.celeryproject.org/en/stable/django/

---

**Last Updated**: Feb 16, 2026  
**KASOKO Version**: 1.0.0-settlement
