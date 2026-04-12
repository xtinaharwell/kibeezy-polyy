# Quick Security Reference Card

## Copy-Paste Integration Templates

### Template 1: Secure Betting Endpoint
```python
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from api.rate_limiting import rate_limit
from api.validators import validate_amount, validate_bet_outcome, ValidationError
from api.audit_logging import AuditLogger, get_client_context
import json

@rate_limit(max_requests=50, window_seconds=3600)  # 50 bets/hour
@require_http_methods(['POST'])
def place_bet(request):
    try:
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        
        data = json.loads(request.body)
        
        # VALIDATE INPUT
        try:
            amount = validate_amount(data.get('amount'))
            outcome = validate_bet_outcome(data.get('outcome'))
            market_id = int(data.get('market_id'))
        except (ValidationError, ValueError) as e:
            return JsonResponse({'error': str(e)}, status=400)
        
        # BUSINESS LOGIC
        if amount > user.balance:
            return JsonResponse({'error': 'Insufficient balance'}, status=400)
        
        market = Market.objects.get(id=market_id)
        if market.status != 'OPEN':
            return JsonResponse({'error': 'Market not open'}, status=400)
        
        # CREATE BET
        bet = Bet.objects.create(market=market, user=user, amount=amount, outcome=outcome)
        user.balance -= amount
        user.save()
        
        # LOG AUDIT TRAIL
        ip, ua = get_client_context(request)
        AuditLogger.log_bet_placed(user, bet, market, amount, ip, ua)
        
        return JsonResponse({'status': 'success', 'bet_id': bet.id})
    
    except Exception as e:
        logger.error(str(e))
        return JsonResponse({'error': 'Server error'}, status=500)
```

### Template 2: Secure Payment Endpoint
```python
from api.rate_limiting import rate_limit_payments
from api.validators import validate_phone_number, validate_amount, ValidationError

@rate_limit_payments  # 10 payments/hour
@require_http_methods(['POST'])
def initiate_deposit(request):
    try:
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        
        data = json.loads(request.body)
        
        # VALIDATE INPUT
        try:
            phone = validate_phone_number(data.get('phone'))
            amount = validate_amount(data.get('amount'))
        except ValidationError as e:
            return JsonResponse({'error': e.message}, status=400)
        
        # CREATE TRANSACTION
        transaction = Transaction.objects.create(
            user=user, type='DEPOSIT', amount=amount, phone_number=phone
        )
        
        # PROCESS PAYMENT
        checkout_id = initiate_mpesa_stk(phone, int(amount))
        transaction.checkout_request_id = checkout_id
        transaction.save()
        
        # LOG AUDIT
        ip, ua = get_client_context(request)
        AuditLogger.log_deposit(user, transaction, amount, ip, ua)
        
        return JsonResponse({'status': 'success'})
    
    except Exception as e:
        logger.error(str(e))
        return JsonResponse({'error': 'Server error'}, status=500)
```

### Template 3: Secure Auth Endpoint
```python
from api.rate_limiting import rate_limit_auth_attempts
from api.validators import validate_phone_number, validate_full_name, ValidationError

@rate_limit_auth_attempts  # 5 attempts/15min
@require_http_methods(['POST'])
def signup(request):
    try:
        data = json.loads(request.body)
        
        # VALIDATE INPUT
        try:
            phone = validate_phone_number(data.get('phone'))
            name = validate_full_name(data.get('name'))
            pin = data.get('pin')
            if not pin or len(pin) < 4:
                raise ValidationError('PIN must be 4+ digits')
        except ValidationError as e:
            return JsonResponse({'error': e.message}, status=400)
        
        # CHECK DUPLICATE
        if CustomUser.objects.filter(phone_number=phone).exists():
            return JsonResponse({'error': 'Phone already registered'}, status=400)
        
        # CREATE USER
        user = CustomUser.objects.create_user(
            phone_number=phone, full_name=name, password=pin
        )
        
        # LOG AUDIT
        ip, ua = get_client_context(request)
        AuditLogger.log_financial_transaction(
            'USER_REGISTERED', user, 0, 'users.CustomUser', user.id,
            description='User signup', ip_address=ip, user_agent=ua
        )
        
        return JsonResponse({'status': 'success', 'user_id': user.id})
    
    except Exception as e:
        logger.error(str(e))
        return JsonResponse({'error': 'Server error'}, status=500)
```

---

## Security Issues & Fixes

| Issue | Symptom | Fix |
|-------|---------|-----|
| No rate limiting | Many requests from same user | Add `@rate_limit()` or `@rate_limit_payments` |
| No audit trail | Can't track who did what | Add `AuditLogger.log_*()` calls |
| Weak validation | Invalid data accepted | Use `validate_*()` functions |
| SQL injection risk | Unusual data in logs | Use Django ORM (parameterized) |
| XSS vulnerability | Your React frontend | Already safe (auto-escapes) |
| No error logging | Silent failures | Use `logger.error()` |
| Rate limit header | Client doesn't know limits | Decorator adds headers automatically |

---

## Deployment Checklist

```bash
# 1. Install requirements
pip install django-redis  # For better caching
pip install bleach  # For HTML sanitization (optional)

# 2. Create logs directory
mkdir -p logs
chmod 755 logs

# 3. Run migrations
python manage.py migrate

# 4. Test on localhost
python manage.py runserver

# 5. Check for security issues
python manage.py check --deploy

# 6. Update .env for production
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
DEBUG=False

# 7. Deploy to production (Render/Railway/etc)
git push origin main  # Or your deployment method
```

---

## Testing Rate Limiting

```bash
# Test endpoint with 60 requests in 3 seconds
# Should see 429 response after limit exceeded

for i in {1..60}; do
  curl -X POST https://your-api.com/api/bets/ \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"market_id":1,"outcome":"Yes","amount":100}' &
  
  if [ $((i % 10)) -eq 0 ]; then
    echo "Sent $i requests..."
    sleep 1
  fi
done

# Look for: 429 Too Many Requests
# Check X-RateLimit headers in response
```

---

## Viewing Audit Logs

```bash
# View recent high-severity events
python manage.py shell
from audit.models import AuditLog
from django.utils import timezone
from datetime import timedelta

# Last 24 hours of critical events
recently = timezone.now() - timedelta(days=1)
critical = AuditLog.objects.filter(
    severity='CRITICAL',
    created_at__gte=recently
).order_by('-created_at')

for log in critical[:10]:
    print(f"{log.created_at} - {log.action} by {log.user}")
    print(f"  {log.description}")
    print(f"  IP: {log.ip_address}")
    print()
```

---

## Production Settings

Set these in your `.env` file:

```bash
# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
DEBUG=False
SECRET_KEY=your-super-secret-key-here

# CORS (adjust for your domain)
CORS_ALLOWED_ORIGINS=https://cache.co.ke,https://www.cache.co.ke
CSRF_TRUSTED_ORIGINS=https://cache.co.ke,https://www.cache.co.ke

# Database (strong password!)
DB_PASSWORD=super-secure-password-123ABC!@#

# M-Pesa (from Daraja)
MPESA_CONSUMER_KEY=your_key
MPESA_CONSUMER_SECRET=your_secret
MPESA_PRODUCTION=True
```

---

## Monitoring Commands

```bash
# Watch security events in real-time
tail -f logs/security.log | grep "WARNING"

# Count rate limit events today
grep "Rate limit exceeded" logs/security.log | wc -l

# Find suspicious IPs
grep "Rate limit exceeded" logs/security.log | grep -o "ip_[^ ]*" | sort | uniq -c

# View all critical audit events
python manage.py shell
from audit.models import AuditLog
AuditLog.objects.filter(severity='CRITICAL').count()

# Export audit trail for compliance
python manage.py dumpdata audit > audit_backup_$(date +%Y%m%d).json
```

---

## Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `ValidationError: Invalid phone` | Wrong format | Use `+254723123456` or `0723123456` |
| `Rate limit exceeded` (429) | Too many requests | Wait for rate limit window to reset |
| `CSRF token missing` | POST without token | Include `X-CSRFToken` header |
| `SSL error in Firefox` | HSTS header | Clear browser site data |
| `Audit log creation failed` | Logs directory missing | `mkdir -p logs && chmod 755 logs` |

---

## Summary

✅ **Rate Limiting** - Prevents brute force & abuse  
✅ **Input Validation** - Stops SQL injection & XSS  
✅ **Audit Logging** - Tracks all transactions  
✅ **Security Headers** - Prevents CSRF, clickjacking, MIME sniffing  
✅ **XSS Protection** - React auto-escapes, validated backend  
✅ **HTTPS Enforcement** - Secure in-transit encryption  

**Your app is now ready for high-traffic production!** 🚀
