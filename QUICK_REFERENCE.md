# KASOKO Quick Reference Guide

## ⚡ Essential Commands

### Terminal 1: Start Redis (Once)
```bash
docker run -d -p 6379:6379 redis:latest
```

### Terminal 2: Start Celery Worker (Continuous)
```bash
cd kibeezy-polyy
celery -A api worker -l info --concurrency=4
```

### Terminal 3: Start Django Dev Server
```bash
cd kibeezy-polyy
python manage.py runserver
```

### Terminal 4 (Optional): Celery Monitoring UI
```bash
pip install flower
celery -A api flower  # Visit http://localhost:5555
```

---

## 🔧 Setup Checklist

```bash
# 1. Start Redis
docker run -d -p 6379:6379 redis:latest

# 2. Set environment variables in .env
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
MPESA_CONSUMER_KEY=your_key
MPESA_CONSUMER_SECRET=your_secret
MPESA_PRODUCTION=False

# 3. Run migrations
python manage.py makemigrations
python manage.py migrate

# 4. Verify system
python verify_system.py

# 5. Start Celery
celery -A api worker -l info --concurrency=4

# 6. Start Django (separate terminal)
python manage.py runserver
```

---

## 📋 Key Files & Locations

| Component | File | Purpose |
|-----------|------|---------|
| **B2C Integration** | `payments/daraja_b2c.py` | M-Pesa API calls |
| **Settlement Engine** | `payments/settlement_tasks.py` | Pari-mutuel calculations |
| **Callback Handler** | `payments/views.py` | B2C callback endpoint |
| **Admin Endpoints** | `markets/admin_settlement_views.py` | Admin settlement UI |
| **Configuration** | `api/settings.py` | Redis/Celery/M-Pesa config |
| **Celery App** | `api/celery.py` | Celery initialization |

---

## 🔐 Environment Variables Required

```env
# Redis (Celery broker & backend)
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1

# M-Pesa Daraja (from Daraja console)
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_INITIATOR_NAME=testapi  # Default test initiator
MPESA_PAYBILL=600000  # Your M-Pesa till number
MPESA_PRODUCTION=False  # True for production

# M-Pesa Security
MPESA_SECURITY_CREDENTIAL_ENCRYPTED=base64_encrypted_password
MPESA_CALLBACK_URL=https://kasoko.app/api/payments/b2c-callback/

# Payout Settings
PAYOUT_PLATFORM_FEE_PCT=5.00  # 5% platform fee
PAYOUT_MIN_AMOUNT=10  # 10 KES minimum payout
```

---

## 📊 Market Settlement Flow

```
Market Closed
  ↓
POST /api/markets/admin/resolve/ {"market_id": 1, "outcome": "Yes"}
  ↓
Celery: settle_market(1)
  - Calculate payouts (pari-mutuel)
  - Create Transaction records
  - Enqueue B2C calls
  ↓
Celery: send_b2c_payout() [×N]
  - Call M-Pesa Daraja B2C API
  - Store conversation_id
  ↓
POST /api/payments/b2c-callback/
  - Verify result_code
  - Mark transaction COMPLETED/FAILED
  - Credit user wallet
  ↓
User receives payout
```

---

## 🧪 Quick Test

```bash
# 1. Create test market & bets (django shell)
python manage.py shell
```

```python
from markets.models import Market, Bet
from users.models import CustomUser
from decimal import Decimal

user1 = CustomUser.objects.create_user(
    phone_number='254712345678', 
    full_name='User 1', 
    pin='1234'
)
user1.balance = Decimal('1000')
user1.save()

market = Market.objects.create(
    question="Will it rain?",
    category="Environment",
    status="CLOSED",  # ← Must be CLOSED to resolve
    end_date="2026-02-17"
)

Bet.objects.create(user=user1, market=market, outcome="Yes", amount=100)

print(f"Market {market.id} created")
```

```bash
# 2. Trigger settlement
curl -X POST http://127.0.0.1:8000/api/markets/admin/resolve/ \
  -H "Content-Type: application/json" \
  -d '{"market_id": 1, "outcome": "Yes"}'
```

```bash
# 3. Watch Celery worker console for:
# [INFO/MainProcess] Task settle_market ...
# [INFO/MainProcess] Settling market 1 ...
# [INFO/MainProcess] Task send_b2c_payout ...
```

---

## 🐛 Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `ConnectionError: Error 111 connecting to 127.0.0.1:6379` | Start Redis: `docker run -d -p 6379:6379 redis:latest` |
| `Task received but never executes` | Start Celery worker: `celery -A api worker -l info` |
| `MPESA_CONSUMER_KEY not found` | Add to .env: `MPESA_CONSUMER_KEY=your_key` |
| `Market not CLOSED` | Verify market.status='CLOSED' before resolve |
| `Market already resolved` | Can't re-resolve; create new market |
| `Callback not received` | Check firewall, HTTPS, public URL |

---

## 🔍 Debugging

### Check Redis
```bash
redis-cli ping  # Should return PONG
redis-cli info  # Check memory, connected clients
```

### Check Celery Tasks
```bash
celery -A api inspect active  # Running tasks
celery -A api inspect reserved  # Queued tasks
celery -A api inspect stats  # Worker stats
```

### Check Django Admin
```bash
# Create superuser
python manage.py createsuperuser

# Access: http://localhost:8000/admin
# - View CustomUser.balance
# - View Transaction records
# - View Market status
# - View Bet records
```

---

## 📈 Performance Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Settlement → First payout | <1s | ? |
| B2C API call | 2-5s | ? |
| M-Pesa processing | 5-30s | ? |
| Callback delivery | <1m | ? |
| Payout success rate | >99% | ? |

Check these after first full test cycle.

---

## 🚀 Deployment Steps (Production)

1. [ ] Update `.env`: Set `MPESA_PRODUCTION=True`
2. [ ] Update `.env`: Set real M-Pesa credentials
3. [ ] Set up HTTPS (Let's Encrypt)
4. [ ] Configure Daraja B2C callback URL to HTTPS
5. [ ] Load test with 100+ concurrent settlements
6. [ ] Monitor payout success rate >99%
7. [ ] Set up alerts for failed payouts
8. [ ] Daily balance reconciliation

---

## 📞 Contact Points

- **Daraja API Docs**: https://developer.safaricom.co.ke
- **Celery Docs**: https://docs.celeryproject.org
- **Redis Docs**: https://redis.io/docs

---

## ✅ Verification Checklist

Before moving to next phase:

- [ ] Redis running: `redis-cli ping` → PONG
- [ ] Celery worker running: see "[*] Ready to accept tasks!"
- [ ] Django server running: http://localhost:8000 works
- [ ] Migrations done: no pending migrations
- [ ] System verified: `python verify_system.py` → all pass
- [ ] Environment variables: `.env` has all required vars
- [ ] URLs configured: `markets/urls.py` has admin routes
- [ ] Test market created: can access via shell
- [ ] Settlement test: admin/resolve endpoint returns task_id

---

**Last Updated**: Feb 16, 2026  
**Version**: 1.0 - Settlement System Ready
