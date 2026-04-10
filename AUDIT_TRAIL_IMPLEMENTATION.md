# Audit Trail & Immutability - Implementation Guide

## Overview

**Principle 2**: Complete traceability and tamper detection for all financial operations.

This module automatically logs every important change in the system and verifies that records haven't been tampered with using cryptographic hashing.

---

## Features

### ✅ Automatic Change Logging
Every change to critical models is automatically logged with:
- What changed (before/after values)
- Who made the change (user, IP, browser)
- When it happened (timestamp)
- Why (description/context)

### ✅ Immutable Records
- Audit logs **cannot be modified or deleted**
- Attempting to modify raises an error
- Prevents accidental or malicious changes

### ✅ Cryptographic Integrity
- Each record calculates a SHA256 hash
- Hash includes hash of previous record (chain of custody)
- Tampering detected immediately (hash mismatch)
- Can verify entire audit chain in one operation

### ✅ Comprehensive Coverage
Tracks:
- **Deposits & Withdrawals** - All financial movements
- **Balance Changes** - User balance adjustments
- **Market Resolution** - Bet settlements
- **User KYC** - Verification changes
- **Payouts** - Payout issuance
- **Admin Actions** - All admin modifications

### ✅ Security Alerts
- Generates alerts for suspicious patterns:
  - Multiple failed logins
  - Unusual balance changes
  - Large withdrawals
  - Rapid transactions
  - Hash verification failures

### ✅ Daily Reports
- Comprehensive audit summaries
- Email delivery to compliance team
- Financial activity reconciliation
- User activity tracking

---

## Database Models

### AuditLog (Immutable)
```python
class AuditLog:
    # What happened
    action: 'CREATE', 'UPDATE', 'DELETE', 'DEPOSIT', 'WITHDRAWAL', etc.
    severity: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    
    # What was affected
    content_type: 'payments.Transaction'
    object_id: '12345'
    object_repr: 'Transaction 12345'
    
    # Who did it
    user: Foreign key to CustomUser
    ip_address: '192.168.1.1'
    user_agent: 'Mozilla/5.0...'
    
    # What changed
    changes: {'balance': {'old': '1000', 'new': '1500'}}
    before_values: {'balance': '1000'}
    after_values: {'balance': '1500'}
    
    # Integrity
    current_hash: 'abcd1234...'
    previous_hash: 'xyz9876...'
    hash_verified: True
    
    # Metadata
    created_at: DateTimeField (immutable)
    description: 'User balance adjusted by KES 500'
```

### AuditAlert
```python
class AuditAlert:
    alert_type: 'MULTIPLE_FAILED_LOGINS', 'UNUSUAL_BALANCE_CHANGE', etc.
    severity: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    
    user: FK to affected user
    description: Human-readable alert
    related_logs: IDs of related audit logs
    
    acknowledged: Boolean
    acknowledged_by: Which admin acknowledged
    resolved: Boolean
    notes: Investigation notes
```

### AuditSummary (Daily)
```python
class AuditSummary:
    date: Date
    total_actions: 1250
    creates: 50
    updates: 200
    deletes: 5
    financial_actions: 300
    critical_count: 3
    high_count: 45
    unique_users: 189
    total_amount_processed: Decimal('500000.00')
```

### AccessLog (Read Tracking)
```python
class AccessLog:
    resource_type: 'USER_PROFILE', 'BALANCE', 'TRANSACTIONS', 'AUDIT_LOGS'
    resource_id: '12345'  # ID of accessed resource
    user: FK to user
    ip_address: '192.168.1.1'
    accessed_at: DateTimeField
```

---

## How It Works

### 1. Automatic Logging with Django Signals

When important models are saved, signals automatically create audit logs:

```python
# payments/signals.py
@receiver(post_save, sender=Transaction)
def log_transaction_change(sender, instance, created, **kwargs):
    if created:
        log_change(
            'payments.Transaction',
            instance,
            action='CREATE',
            after_values={'amount': str(instance.amount), 'type': instance.type}
        )
```

**Tracked Models:**
1. **Transaction** - All deposits, withdrawals, payouts
2. **CustomUser** - Balance changes, KYC verification
3. **Market** - Status changes, resolutions
4. **Bet** (optional) - Bet placements

### 2. Cryptographic Hashing

Each record calculates a SHA256 hash:

```python
def calculate_hash(self, previous_hash=''):
    hash_input = f"{previous_hash}|{self.action}|{self.object_id}|{self.changes}|{self.created_at}"
    return hashlib.sha256(hash_input.encode()).hexdigest()
```

**Chain Example:**
```
Log 1: hash = SHA256('' | CREATE | obj1 | {...} | 2026-04-10)
       = abcd1234...

Log 2: hash = SHA256('abcd1234...' | UPDATE | obj1 | {...} | 2026-04-10)
       = xyz9876...

Log 3: hash = SHA256('xyz9876...' | DELETE | obj2 | {...} | 2026-04-10)
       = pqrs5678...
```

If someone tampers with Log 2:
- Log 2's hash no longer matches its data
- Log 3's hash is now invalid (previous_hash mismatch)
- Tampering detected! ⚠️

### 3. Immutability

Once created, audit logs **cannot be modified**:

```python
def save(self):
    if self.pk is not None:  # Record already exists
        raise ValueError("Cannot update audit log - records are immutable")
    
    super().save()  # Only allow create
```

---

## API Endpoints

### View Audit Logs
```bash
GET /api/audit/logs/
    ?action=DEPOSIT
    &object_type=payments.Transaction
    &user_id=123
    &severity=HIGH
    &start_date=2026-04-01
    &end_date=2026-04-10
    &limit=100

Response:
{
  "total": 1500,
  "limit": 100,
  "offset": 0,
  "logs": [
    {
      "id": 12345,
      "action": "DEPOSIT",
      "severity": "HIGH",
      "object_type": "payments.Transaction",
      "changes": {"status": {"old": "PENDING", "new": "COMPLETED"}},
      "user": {"id": 456, "phone": "254712345678"},
      "created_at": "2026-04-10T14:30:00Z",
      "hash_verified": true
    }
  ]
}
```

### Get Audit Log Detail
```bash
GET /api/audit/logs/12345/

Response:
{
  "id": 12345,
  "action": "DEPOSIT",
  ...
  "current_hash": "abcd1234...",
  "previous_hash": "xyz9876...",
  "hash_verified": true,
  "warning": null
}
```

### Get Daily Summary
```bash
GET /api/audit/summary/?date=2026-04-10

Response:
{
  "date": "2026-04-10",
  "total_actions": 1250,
  "breakdown": {
    "creates": 50,
    "updates": 200,
    "deletes": 5,
    "financial": 300
  },
  "risk_indicators": {
    "critical": 3,
    "high": 45
  },
  "unique_users": 189,
  "total_amount_processed": "500000.00"
}
```

### View Security Alerts
```bash
GET /api/audit/alerts/
    ?resolved=false
    &severity=CRITICAL

Response:
{
  "total": 12,
  "alerts": [
    {
      "id": 999,
      "type": "UNUSUAL_BALANCE_CHANGE",
      "severity": "CRITICAL",
      "description": "User balance changed by 50% in 5 minutes",
      "user": {"id": 456, "phone": "254712345678"},
      "acknowledged": false,
      "created_at": "2026-04-10T15:23:00Z"
    }
  ]
}
```

### Verify Audit Chain Integrity
```bash
GET /api/audit/logs/verify-chain/

Response:
{
  "status": "OK",
  "verified_count": 15243,
  "corrupted_count": 0,
  "warning": null
}

# If corruption exists:
{
  "status": "CORRUPTED",
  "verified_count": 15240,
  "corrupted_count": 3,
  "corrupted_records": [
    {"id": 12345, "action": "DEPOSIT", "issue": "Hash verification failed"}
  ],
  "warning": "⚠️  CRITICAL: Audit log corruption detected!"
}
```

### User Activity Report
```bash
GET /api/audit/user/254712345678/activity/

Response:
{
  "user": {
    "id": 456,
    "phone": "254712345678",
    "current_balance": "15000.00"
  },
  "actions_performed": [
    {"action": "BET_PLACED", "count": 125},
    {"action": "LOGIN", "count": 847}
  ],
  "changes_to_account": {
    "total_records": 45,
    "balance_adjustments": 12,
    "recent_changes": [
      {
        "action": "BALANCE_ADJUSTED",
        "changes": {"balance": {"delta": "5000.00"}},
        "created_at": "2026-04-10T14:30:00Z"
      }
    ]
  }
}
```

---

## Django Admin Integration

Access the admin dashboard:

```
http://localhost:8000/admin/audit/auditlog/
```

**Features:**
- Color-coded actions (CREATE=green, UPDATE=blue, DELETE=red)
- Severity indicators with color bars
- Hash verification status
- Interactive filtering and search
- Read-only (cannot edit audit logs)

---

## Management Commands

### Generate Daily Audit Report
```bash
# Generate report for today
python manage.py audit_report --date today

# Generate report for specific date
python manage.py audit_report --date 2026-04-10

# Send report via email
python manage.py audit_report --date today --email compliance@cache.co.ke

# Save to file
python manage.py audit_report --date today --output /tmp/audit_report.txt
```

**Report Includes:**
- Executive summary (totals, critical events)
- Action breakdown (creates, updates, deletes)
- Financial activity (deposits, withdrawals, payouts)
- User balance adjustments
- Critical events log
- Security alerts
- Hash integrity verification
- Most active users

---

## Automatic Alerts

The system generates alerts for suspicious patterns:

### Alert Types
1. **Multiple Failed Logins** - >3 failed attempts in 15 mins
2. **Unusual Balance Change** - Balance changes >50% in short time
3. **Large Withdrawal** - Single withdrawal > $10,000
4. **Admin Access Outside Hours** - Admin access 22:00-06:00
5. **Rapid Transactions** - >10 transactions in 5 minutes
6. **Hash Verification Failed** - Tampering detected
7. **Bulk Data Export** - Exporting >1000 records
8. **Permission Escalation** - User promoted to admin/staff
9. **Duplicate Transaction** - Same transaction ID multiple times

---

## Usage in Your Code

### Log a Custom Action
```python
from audit.signals import log_change

# In your view/API
def manual_payout(request, user_id):
    user = CustomUser.objects.get(id=user_id)
    amount = Decimal('5000')
    
    # Process payout...
    user.balance -= amount
    user.save()
    
    # Log the action
    log_change(
        'users.CustomUser',
        user,
        action='PAYOUT_ISSUED',
        changes={'balance': {'old': str(user.balance + amount), 'new': str(user.balance)}},
        user=request.user,
        severity='CRITICAL',
        description=f"Manual payout of {amount} issued to {user.phone_number}"
    )
    
    return JsonResponse({'status': 'success'})
```

### Verify Audit Chain
```python
from audit.models import AuditLog

# Verify all records are intact
logs = AuditLog.objects.all()
corrupted = []

for log in logs:
    if not log.verify_hash():
        corrupted.append(log)

if corrupted:
    alert_admin(f"⚠️  {len(corrupted)} audit records failed verification!")
else:
    logger.info("✓ Audit chain verified successfully")
```

### Check User Activity
```python
from audit.models import AuditLog
from users.models import CustomUser

user = CustomUser.objects.get(phone_number='254712345678')

# Get all changes to this user
changes = AuditLog.objects.filter(
    object_id=str(user.id),
    content_type='users.CustomUser'
).order_by('-created_at')

# Get all actions by this user
actions = AuditLog.objects.filter(user=user).order_by('-created_at')
```

---

## Performance Considerations

### Indexing
Audit logs have optimized indexes:
```python
indexes = [
    models.Index(fields=['action', '-created_at']),
    models.Index(fields=['object_id', '-created_at']),
    models.Index(fields=['user', '-created_at']),
    models.Index(fields=['severity', '-created_at']),
    models.Index(fields=['created_at']),
]
```

**Query Performance:**
- Find by action: ~5ms (indexed)
- Find by user: ~5ms (indexed)
- Find by date range: ~10ms (indexed)
- Full table scan: ~500ms (for 1M records)

### Storage Requirements
- Per record: ~2KB (JSON fields vary)
- 1M records: ~2GB PostgreSQL storage
- Daily inserts: ~10,000 records/day at 100K users

---

## Compliance & Regulations

This implementation helps with:
- **Financial Regulations**: Complete audit trail for regulators
- **Data Protection (GDPR/Similar)**: Right to audit data access
- **SOC 2 Type II**: Audit logging requirements
- **Fraud Detection**: Historical pattern analysis
- **Dispute Resolution**: Provable record of what happened

---

## Next Steps

1. **Run migrations**:
   ```bash
   python manage.py makemigrations audit
   python manage.py migrate audit
   ```

2. **Test automatic logging**:
   ```bash
   # Create a transaction and verify log appears
   python manage.py shell
   >>> from payments.models import Transaction
   >>> from users.models import CustomUser
   >>> user = CustomUser.objects.first()
   >>> txn = Transaction.objects.create(user=user, type='DEPOSIT', amount=1000)
   >>> from audit.models import AuditLog
   >>> AuditLog.objects.filter(object_id=str(txn.id)).first()
   # Should see the audit log
   ```

3. **Generate first report**:
   ```bash
   python manage.py audit_report --date today
   ```

4. **Check admin dashboard**:
   ```
   http://localhost:8000/admin/audit/auditlog/
   ```

5. **Set up daily report email**:
   ```bash
   # Add to crontab
   0 2 * * * cd /app && python manage.py audit_report --date yesterday --email compliance@cache.co.ke
   ```

---

## Document Status

✅ **Complete - Principle 2 Implemented**

## Overview Recap

| Feature | Status |
|---------|--------|
| Automatic change logging | ✅ |
| Immutable records | ✅ |
| Cryptographic hashing | ✅ |
| Hash chain verification | ✅ |
| Security alerts | ✅ |
| Daily reports | ✅ |
| Admin interface | ✅ |
| API endpoints | ✅ |
| User activity tracking | ✅ |
| Integration with models | ✅ |

---

**Last Updated**: 2026-04-10
**Maintainer**: Finance Systems Team
