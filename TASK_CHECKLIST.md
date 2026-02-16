# KASOKO Development Task Checklist

## Phase 1: Infrastructure Setup (IMMEDIATE - DO THIS FIRST)

### 1.1 Redis Setup ⏳
- [ ] Install Redis (Docker recommended: `docker run -d -p 6379:6379 redis:latest`)
- [ ] Test connection: `redis-cli ping` (should return PONG)
- [ ] Verify ports open: 6379 for broker, 6379 for backend

### 1.2 Database Migrations ⏳
- [ ] Ensure Transaction model has `external_ref` field with `unique=True`
- [ ] Check models.py for `mpesa_response` JSONField in Transaction
- [ ] Run: `python manage.py makemigrations`
- [ ] Run: `python manage.py migrate`
- [ ] Verify in Django shell: `python manage.py shell`
  ```python
  from payments.models import Transaction
  print(Transaction._meta.fields)  # Confirm external_ref and mpesa_response exist
  ```

### 1.3 Environment Variables ⏳
- [ ] Create/update `.env` file in `kibeezy-polyy/` with:
  - CELERY_BROKER_URL
  - CELERY_RESULT_BACKEND
  - MPESA_CONSUMER_KEY/SECRET (sandbox for now)
  - MPESA_INITIATOR_NAME
  - MPESA_SECURITY_CREDENTIAL_ENCRYPTED
  - MPESA_PAYBILL
  - MPESA_PRODUCTION=False (use sandbox)
  - PAYOUT_PLATFORM_FEE_PCT=5.00
  - PAYOUT_MIN_AMOUNT=10
- [ ] Verify `api/settings.py` imports from env variables correctly
- [ ] Test in Django shell: `from django.conf import settings; print(settings.CELERY_BROKER_URL)`

### 1.4 Install Python Dependencies ⏳
```bash
pip install celery redis cryptography requests
# Or: pip install -r requirements.txt (if requirements.txt already updated)
```

---

## Phase 2: Wire Up Admin Endpoints (HIGH PRIORITY)

### 2.1 Add URLs to markets/urls.py ⏳
- [ ] Open `kibeezy-polyy/markets/urls.py`
- [ ] Add imports:
  ```python
  from markets.admin_settlement_views import (
      resolve_market,
      settlement_status,
      retry_payout,
      retry_failed_payouts_batch
  )
  ```
- [ ] Add URL patterns:
  ```python
  path('admin/resolve/', resolve_market, name='resolve_market'),
  path('admin/settlement-status/<int:market_id>/', settlement_status, name='settlement_status'),
  path('admin/retry-payout/', retry_payout, name='retry_payout'),
  path('admin/retry-failed-payouts/', retry_failed_payouts_batch, name='retry_failed_payouts'),
  ```

### 2.2 Add URLs to payments/urls.py ⏳
- [ ] Open `kibeezy-polyy/payments/urls.py`
- [ ] Ensure `b2c-callback/` route exists (should already be added)
  ```python
  path('b2c-callback/', b2c_result_callback, name='b2c_callback'),
  ```

### 2.3 Test Admin Endpoints ⏳
- [ ] Create test market in Django shell (see SETTLEMENT_IMPLEMENTATION.md section 4.1)
- [ ] Test resolve endpoint: `POST /api/markets/admin/resolve/` with `{"market_id": 1, "outcome": "Yes"}`
- [ ] Expected response: `{"status": "resolved", "market_id": 1, "settlement_task_id": "..."}`

---

## Phase 3: Start Celery Worker (HIGH PRIORITY)

### 3.1 Start Redis ⏳
```bash
docker run -d -p 6379:6379 redis:latest
# Verify: redis-cli ping
```

### 3.2 Start Celery Worker ⏳
Open **NEW TERMINAL**:
```bash
cd kibeezy-polyy
celery -A api worker -l info --concurrency=4
```
Expected output:
```
celery@<hostname> v5.x.x (twill)
[... celery initialization ...]
[*] Ready to accept tasks!
```

### 3.3 Monitor Worker ⏳
- [ ] Celery worker running and logging task executions
- [ ] No connection errors to Redis
- [ ] Test with: `python manage.py shell` → `from api.celery import app; app.control.inspect().active()` (shows active tasks)

---

## Phase 4: Implement Bet Placement API (HIGH PRIORITY)

### 4.1 Create Bet Placement Endpoint ⏳
File: `kibeezy-polyy/markets/views.py`

Add function:
```python
@login_required
@require_http_methods(["POST"])
def place_bet(request):
    """
    POST /api/markets/place-bet/
    {
        "market_id": 1,
        "outcome": "Yes",
        "amount": 100
    }
    """
    try:
        data = json.loads(request.body)
        market_id = data.get('market_id')
        outcome = data.get('outcome')
        amount = Decimal(str(data.get('amount')))
        
        # Validation
        if amount <= 0:
            return JsonResponse({'error': 'Amount must be positive'}, status=400)
        
        market = Market.objects.get(id=market_id)
        if market.status != 'OPEN':
            return JsonResponse({'error': 'Market not open'}, status=400)
        
        # Check balance
        if request.user.balance < amount:
            return JsonResponse({'error': 'Insufficient balance'}, status=400)
        
        # Deduct balance atomically
        with transaction.atomic():
            user = CustomUser.objects.select_for_update().get(id=request.user.id)
            if user.balance < amount:
                raise Exception('Insufficient balance')
            
            user.balance -= amount
            user.save()
            
            bet = Bet.objects.create(
                user=user,
                market=market,
                outcome=outcome,
                amount=amount,
                status='PENDING'
            )
        
        return JsonResponse({
            'id': bet.id,
            'market_id': market_id,
            'outcome': outcome,
            'amount': str(amount),
            'user_balance': str(user.balance)
        })
    
    except Market.DoesNotExist:
        return JsonResponse({'error': 'Market not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

### 4.2 Add URL Route ⏳
In `kibeezy-polyy/markets/urls.py`:
```python
path('place-bet/', place_bet, name='place_bet'),
```

### 4.3 Test Bet Placement ⏳
```bash
curl -X POST http://127.0.0.1:8000/api/markets/place-bet/ \
  -H "Content-Type: application/json" \
  -H "X-User-Phone-Number: 254712345678" \
  -d '{
    "market_id": 1,
    "outcome": "Yes",
    "amount": 50
  }'
```

---

## Phase 5: Frontend - Bet Placement UI (MEDIUM PRIORITY)

### 5.1 Create Bet Modal Component ⏳
File: `kibeezy-poly/components/BetModal.tsx`

Features:
- [ ] Show market question
- [ ] Input for bet amount
- [ ] Select outcome (Yes/No)
- [ ] Show current balance
- [ ] Confirm button with loading state
- [ ] Error/success messages

### 5.2 Update Market Page ⏳
File: `kibeezy-poly/app/dashboard/page.tsx`

- [ ] Add state for selected market to show modal
- [ ] Integrate BetModal component
- [ ] Call API on confirm using `fetchWithAuth`

### 5.3 Update MarketCard Component ⏳
File: `kibeezy-poly/components/MarketCard.tsx`

- [ ] Add "Place Bet" button
- [ ] Trigger modal on click

---

## Phase 6: Frontend - Transaction History (MEDIUM PRIORITY)

### 6.1 Create Transaction History Page ⏳
File: `kibeezy-poly/app/transactions/page.tsx`

Features:
- [ ] List all user transactions (deposits, bets, payouts)
- [ ] Show status (PENDING, COMPLETED, FAILED)
- [ ] Show amounts, dates
- [ ] Filter by type (deposit/bet/payout)

### 6.2 Update Backend API ⏳
File: `kibeezy-polyy/payments/views.py`

Add endpoint:
```python
@login_required
@require_http_methods(["GET"])
def get_transactions(request):
    """
    GET /api/payments/transactions/?status=COMPLETED&type=payout&limit=50
    """
    user = request.user
    status = request.GET.get('status')
    tx_type = request.GET.get('type')
    limit = int(request.GET.get('limit', 50))
    
    txs = Transaction.objects.filter(user=user)
    
    if status:
        txs = txs.filter(status=status)
    if tx_type:
        txs = txs.filter(type=tx_type)
    
    return JsonResponse({
        'transactions': [
            {
                'id': tx.id,
                'type': tx.type,
                'amount': str(tx.amount),
                'status': tx.status,
                'created_at': tx.created_at.isoformat(),
                'updated_at': tx.updated_at.isoformat(),
            }
            for tx in txs.order_by('-created_at')[:limit]
        ]
    })
```

---

## Phase 7: Admin Dashboard (LOW PRIORITY)

### 7.1 Create Admin Settlement Dashboard ⏳
File: `kibeezy-poly/app/admin/settlement/page.tsx`

Features:
- [ ] List all markets with status (OPEN/CLOSED/RESOLVED/SETTLEMENT_IN_PROGRESS)
- [ ] Show settlement stats (total pool, winners, payouts)
- [ ] Button to resolve market (modal with outcome selector)
- [ ] Button to view settlement status
- [ ] Button to retry failed payouts

### 7.2 Admin API Calls ⏳
All calls require staff role:
- [ ] POST /api/markets/admin/resolve/
- [ ] GET /api/markets/admin/settlement-status/{id}/
- [ ] POST /api/payments/admin/retry-payout/
- [ ] POST /api/payments/admin/retry-failed-payouts/

---

## Phase 8: Testing & Validation (CRITICAL)

### 8.1 Unit Tests ⏳
- [ ] Test settlement calculation: `Bet(amount=100) + Bet(amount=200) → payout = 100/100 * (300*0.95) = 285`
- [ ] Test B2C callback idempotency: same callback twice → only one credit
- [ ] Test refund logic: market with no winners → all users refunded

### 8.2 Integration Test ⏳
1. [ ] Create market
2. [ ] Place 2 bets (different outcomes)
3. [ ] Admin resolve with one outcome winner
4. [ ] Check settlement task executed
5. [ ] Verify B2C payout initiated
6. [ ] Simulate callback
7. [ ] Check payout transaction COMPLETED
8. [ ] Check winner's balance credited
9. [ ] Check loser's balance unchanged

### 8.3 Load Test ⏳
- [ ] Simulate 100+ concurrent settlements
- [ ] Verify no race conditions
- [ ] Check database consistency

---

## Phase 9: Security & Encryption (MEDIUM PRIORITY)

### 9.1 M-Pesa Security Credential Encryption ⏳
- [ ] Download Safaricom public certificate from Daraja
- [ ] Encrypt initiator password using certificate
- [ ] Store encrypted credential in env variable
- [ ] Test B2C API calls use encrypted credential

See SETTLEMENT_IMPLEMENTATION.md section 2.5 for encryption steps.

### 9.2 HTTPS & Callback Security ⏳
- [ ] Set up HTTPS for production (Let's Encrypt)
- [ ] Verify callback URL is HTTPS
- [ ] Implement callback signature verification (if Daraja provides signing key)
- [ ] Add rate limiting to callback endpoint

---

## Phase 10: Production Deployment (FUTURE)

### 10.1 Deployment Checklist ⏳
See SETTLEMENT_IMPLEMENTATION.md Part 6 for full pre-launch checklist

Key items:
- [ ] Set MPESA_PRODUCTION=True
- [ ] Use Daraja production credentials
- [ ] Set DEBUG=False
- [ ] Configure HTTPS
- [ ] Set up monitoring/alerting
- [ ] Load test in production environment
- [ ] Dry-run settlement with small amounts

### 10.2 Ongoing Operations ⏳
- [ ] Daily payout success rate monitoring
- [ ] Weekly failed payout review
- [ ] Monthly audit trail review
- [ ] Quarterly reconciliation with Safaricom

---

## Recommended Execution Order

1. **Today**: Complete Phase 1 (Infrastructure) + Phase 2 (Wire URLs) + Phase 3 (Celery)
2. **Tomorrow**: Complete Phase 4 (Bet API) + Phase 8.2 (Integration Test)
3. **This Week**: Complete Phase 5 (Bet UI) + Phase 6 (Transactions History)
4. **Next Week**: Complete Phase 7 (Admin Dashboard) + Phase 9 (Security)
5. **Pre-Launch**: Complete Phase 10 (Production Deployment)

---

## Quick Reference - Commands to Run

```bash
# Terminal 1: Redis
docker run -d -p 6379:6379 redis:latest

# Terminal 2: Celery Worker
cd kibeezy-polyy
celery -A api worker -l info --concurrency=4

# Terminal 3: Django Dev Server
cd kibeezy-polyy
python manage.py runserver

# Terminal 4: Optional - Celery Flower (monitoring UI)
celery -A api flower

# Django Shell (testing)
python manage.py shell
```

---

## Contact & Notes

Created: Feb 16, 2026  
Status: Actively Maintained  
Next Review: After Phase 3 completion
