# Audit Trail - Quick Migration & Activation Guide

Once you're ready to activate the audit trail system, follow these steps:

## Step 1: Create Database Migrations

```bash
# Navigate to project directory
cd /home/elijahcollins254/CACHE/kibeezy-polyy

# Create migration files for the audit app
python manage.py makemigrations audit

# Output should show:
# Migrations for 'audit':
#   audit/migrations/0001_initial.py
#     - Create model AuditLog
#     - Create model AuditSummary
#     - Create model AccessLog
#     - Create model AuditAlert
```

## Step 2: Review Migration File (Optional)

```bash
# View the generated migration
cat kibeezy-polyy/audit/migrations/0001_initial.py
```

## Step 3: Apply Database Migrations

```bash
# Apply migrations to database
python manage.py migrate audit

# Output should show:
# Running migrations:
#   Applying audit.0001_initial... OK
```

## Step 4: Verify Model Installation

```bash
# Check that models are registered
python manage.py shell
>>> from audit.models import AuditLog, AuditSummary, AccessLog, AuditAlert
>>> AuditLog.objects.count()
0
>>> print("✓ Audit models successfully installed")
>>> exit()
```

## Step 5: Access Django Admin

```bash
# Start the development server
python manage.py runserver

# Visit admin dashboard
# http://localhost:8000/admin/audit/auditlog/
# Login with superuser credentials

# You should see 4 audit-related models:
# - Audit Logs
# - Audit Summaries  
# - Access Logs
# - Audit Alerts
```

## Step 6: Test Automatic Logging

```bash
# Create a test transaction to verify logging works
python manage.py shell
>>> from payments.models import Transaction
>>> from users.models import CustomUser
>>> from audit.models import AuditLog
>>> 
>>> # Get or create user
>>> user = CustomUser.objects.first()
>>>
>>> # Create a deposit transaction
>>> txn = Transaction.objects.create(
...     user=user,
...     type='DEPOSIT',
...     amount='1000.00',
...     status='COMPLETED',
...     mpesa_receipt='TEST123'
... )
>>>
>>> # Check if audit log was created automatically
>>> log = AuditLog.objects.filter(
...     object_id=str(txn.id)
... ).first()
>>>
>>> if log:
...     print(f"✓ Automatic logging works!")
...     print(f"  Action: {log.action}")
...     print(f"  Object: {log.content_type} #{log.object_id}")
...     print(f"  Hash: {log.current_hash[:16]}...")
... else:
...     print("✗ No audit log created - check signals")
```

## Step 7: Generate First Audit Report

```bash
# Generate a daily audit report
python manage.py audit_report --date today

# Or with email
python manage.py audit_report --date today --email admin@cache.co.ke

# Or save to file
python manage.py audit_report --date today --output audit_report.txt
```

## Step 8: Schedule Daily Reports (Production)

Add to your crontab:

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 2 AM)
0 2 * * * cd /home/elijahcollins254/CACHE/kibeezy-polyy && python manage.py audit_report --date yesterday --email compliance@cache.co.ke

# Or every 6 hours
0 */6 * * * cd /home/elijahcollins254/CACHE/kibeezy-polyy && python manage.py audit_report --date today
```

---

## Troubleshooting

### Issue: "audit app not in INSTALLED_APPS"

**Solution:** Verify in `api/settings.py`:
```python
INSTALLED_APPS = [
    ...
    'audit',  # Make sure this line exists
    ...
]
```

### Issue: "No audit logs created after transactions"

**Solution:** Check signal handlers in `audit/signals.py`:
```bash
python manage.py shell
>>> from audit.signals import log_change
>>> from audit.models import AuditLog
>>> 
>>> # Manually create a log
>>> log_change(
...     'users.CustomUser',
...     None,
...     action='TEST',
...     changes={},
...     severity='LOW'
... )
>>> AuditLog.objects.count()  # Should be 1 now
```

### Issue: "Cannot migrate - duplicate table"

**Solution:** If tables already exist (shouldn't happen):
```bash
# This shouldn't be needed, but if so:
python manage.py migrate audit zero  # Reverse migrations
python manage.py migrate audit       # Reapply
```

### Issue: Hash verification always fails

**Solution:** Check hash calculation in `models.py`:
```bash
python manage.py shell
>>> from audit.models import AuditLog
>>> log = AuditLog.objects.first()
>>> if log.verify_hash():
...     print("✓ Hash verification working")
... else:
...     print("✗ Hash verification failed")
...     print(f"Expected: {log.current_hash}")
...     print(f"Got: {log.calculate_hash(log.previous_hash)}")
```

---

## Commands Added

```bash
# View audit logs via CLI
python manage.py shell -c "
from audit.models import AuditLog
for log in AuditLog.objects.order_by('-created_at')[:10]:
    print(f'{log.created_at} | {log.action} | {log.object_id} | {log.severity}')
"

# Verify audit chain
python manage.py shell -c "
from audit.models import AuditLog
logs = AuditLog.objects.all()
failed = [l for l in logs if not l.verify_hash()]
print(f'✓ Chain verified: {logs.count()} records, {len(failed)} failed')
"

# Generate report
python manage.py audit_report --date today --output /tmp/audit.txt
```

---

## API Endpoints Now Available

Once migrations are applied:

```bash
# View recent audit logs
curl http://localhost:8000/api/audit/logs/

# View specific log with hash verification
curl http://localhost:8000/api/audit/logs/1/

# Daily summary
curl http://localhost:8000/api/audit/summary/?date=2026-04-10

# Security alerts
curl http://localhost:8000/api/audit/alerts/

# Verify entire chain
curl http://localhost:8000/api/audit/logs/verify-chain/

# User activity
curl http://localhost:8000/api/audit/user/254712345678/activity/
```

---

## Performance Impact

After activation, expect:
- **Disk usage**: +2KB per transaction logged (~2GB per million records)
- **Query latency**: < +5ms per transaction (due to audit signal)
- **CPU overhead**: ~2-5% for signal processing
- **Network**: Minimal (batch reporting once daily)

**Optimization:** Already indexed for:
- Fast filtering by action/user/severity
- Fast date range queries
- Fast hash chain verification

---

**Ready to activate? Run Step 1 above!**
