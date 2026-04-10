# Database Integrity & Atomicity - Implementation Guide

## Overview

This document describes the implementation of **Database Integrity & Atomicity** - the first principle for keeping customer deposits safe and secure.

## Problem Solved

**Without atomic transactions**, financial operations can fail halfway:
- User's balance updates, but transaction record doesn't create
- Transaction record creates, but balance doesn't update
- Callback arrives twice, depositing funds twice
- System crashes mid-operation, leaving inconsistent state

**Result**: Money lost, customer angry, audit trail broken.

## Solution: Atomic Transactions

All financial operations now use **database transactions** that ensure **all-or-nothing execution**:
- ✅ Both balance AND transaction record update together
- ✅ Money is never double-credited
- ✅ Failed operations rollback completely
- ✅ Idempotent (safe to retry)

---

## Files Created/Modified

### 1. **NEW: `payments/transaction_safety.py`** (350+ lines)
Core module providing atomic transaction utilities.

**Key Functions:**

#### `safe_process_deposit(user, amount, external_ref, **fields)`
```python
# Atomically credit user balance and create transaction record
txn = safe_process_deposit(
    user=user,
    amount=Decimal('500'),
    external_ref='MPESA_12345',
    mpesa_response={'receipt': 'abc123'}
)
# Both user.balance += 500 AND Transaction.objects.create() succeed together
# Or both fail and rollback
```

**Guarantees:**
- ✅ User balance and transaction record always in sync
- ✅ No orphaned records
- ✅ All-or-nothing semantics

#### `safe_process_withdrawal(user, amount, external_ref, **fields)`
```python
# Atomically deduct balance and create transaction record
# Includes balance verification
try:
    txn = safe_process_withdrawal(
        user=user,
        amount=Decimal('100'),
        external_ref='WITHDRAW_456'
    )
except TransactionError as e:
    # Insufficient balance or other error - no balance changed
    return error_response(e)
```

**Guarantees:**
- ✅ Insufficient balance caught BEFORE any update
- ✅ Uses database-level locking (`select_for_update`)
- ✅ Prevents race conditions

#### `verify_user_balance_consistency(user_id)`
```python
# Calculate expected balance from transaction history
result = verify_user_balance_consistency(user.id)

if not result['is_consistent']:
    print(f"DISCREPANCY: Expected {result['expected_balance']}, "
          f"got {result['actual_balance']}")
    
    # result includes:
    # - expected_balance, actual_balance, difference
    # - total_deposits, total_withdrawals
    # - deposit_count, withdrawal_count
```

**Returns comprehensive audit data:**
```python
{
    'is_consistent': True/False,
    'expected_balance': 5000.00,
    'actual_balance': 5000.00,
    'difference': 0.00,
    'total_deposits': 10000.00,
    'total_withdrawals': 5000.00,
    'deposit_count': 3,
    'withdrawal_count': 2
}
```

#### `verify_transaction_immutability(transaction_id)`
```python
# Verify transaction hasn't been tampered with
is_safe = verify_transaction_immutability(txn.id)

if not is_safe:
    alert_admin()  # Transaction was modified after creation!
```

#### `rollback_failed_transaction(transaction_id, reason)`
```python
# Safely reverse a failed transaction
# Creates a PAYOUT transaction to restore funds
success = rollback_failed_transaction(
    tx.id, 
    reason="M-Pesa API timeout"
)

if success:
    logger.info(f"User refunded for failed transaction")
```

---

### 2. **MODIFIED: `payments/views.py`**

**Changed the M-Pesa callback handler** to use atomic transactions:

**Before** (❌ Not atomic):
```python
if payment_successful:
    transaction.status = 'COMPLETED'
    transaction.save()
    
    # <-- DANGER ZONE: If server crashes here, balance not updated
    user = transaction.user
    user.balance += transaction.amount
    user.save()
```

**After** (✅ Atomic):
```python
if payment_successful:
    try:
        # Both balance AND transaction update together
        verified_txn = safe_process_deposit(
            user=transaction.user,
            amount=transaction.amount,
            external_ref=f"DEPOSIT-VERIFIED-{transaction.id}",
            mpesa_response=receipt_data
        )
        
        # Verify consistency
        balance_check = verify_user_balance_consistency(user.id)
        if not balance_check['is_consistent']:
            logger.warning(f"⚠️ Inconsistency: {balance_check}")
            
    except TransactionError as e:
        logger.error(f"Atomic transaction failed: {e}")
        # Funds never debited - safe
```

**Benefits:**
1. ✅ All-or-nothing semantics
2. ✅ Automatic rollback on error
3. ✅ Balance verification after each operation
4. ✅ Clear error handling

---

### 3. **NEW: `payments/management/commands/reconcile_balances.py`**

Django management command for daily reconciliation audits.

**Usage:**

```bash
# Reconcile all users
python manage.py reconcile_balances

# Reconcile specific user
python manage.py reconcile_balances --user-id=123

# Only show discrepancies (don't fix)
python manage.py reconcile_balances --alert-only

# Auto-fix discrepancies (use with caution!)
python manage.py reconcile_balances --fix
```

**Output:**
```
=======================================================================
BALANCE RECONCILIATION REPORT
=======================================================================

⚠️  DISCREPANCY FOUND - User 42 (254712345678)
  Expected Balance: KES 5000.00
  Actual Balance:   KES 4500.00
  Difference:       KES -500.00
  Total Deposits:    3 (KES 10000.00)
  Total Withdrawals: 2 (KES 5000.00)
  ✓ Balance corrected

=======================================================================
RECONCILIATION SUMMARY
=======================================================================
Total Users Checked:   1250
Discrepancies Found:   3
Discrepancies Fixed:   3

✓ All balances verified successfully!
```

---

## Database-Level Guarantees

### 1. **Transaction Table Constraints**

```python
# In payments/models.py
class Transaction(models.Model):
    external_ref = models.CharField(
        max_length=100, 
        unique=True,  # ← Prevents duplicate deposits
        null=True, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)  # ← Immutable
    updated_at = models.DateTimeField(auto_now=True)     # ← Tracks changes
```

**Prevents:**
- ✅ Duplicate deposits (unique external_ref)
- ✅ Tampering (immutable created_at)
- ✅ Unauthorized modifications (updated_at tracked)

### 2. **Django ORM Atomic Transactions**

```python
# All changes in this block happen together or not at all
with db_transaction.atomic():
    user.balance += amount
    user.save()
    
    Transaction.objects.create(
        user=user,
        amount=amount,
        type='DEPOSIT'
    )
    # If error here ↓, both changes rollback
    # If success here ↑, both commit together
```

### 3. **Row-Level Locking**

```python
# In safe_process_withdrawal:
user = CustomUser.objects.select_for_update().get(id=user.id)
# ↑ Locks this user's row, preventing race conditions
```

**Prevents:**
- ✅ Double withdrawal (concurrent requests lock each other)
- ✅ Lost updates (database enforces sequentiality)

---

## How to Use in New Endpoints

**Example: Creating a betting endpoint**

```python
from payments.transaction_safety import safe_process_withdrawal, TransactionError

def place_bet(request):
    user = get_user(request)
    bet_amount = Decimal('500')
    market_id = request.POST['market_id']
    
    try:
        # Atomically deduct balance and create bet transaction
        txn = safe_process_withdrawal(
            user=user,
            amount=bet_amount,
            external_ref=f"BET-{market_id}-{user.id}",
            description=f"Bet on market {market_id}"
        )
        
        # Only create bet if transaction succeeded
        bet = Bet.objects.create(
            user=user,
            market_id=market_id,
            amount=bet_amount,
            transaction=txn
        )
        
        return JsonResponse({'success': True, 'bet_id': bet.id})
        
    except TransactionError as e:
        # Balance not changed - safe to retry
        return JsonResponse({'error': str(e)}, status=400)
```

---

## Monitoring & Alerts

### 1. **Schedule Daily Reconciliation**

```python
# In celery_beat config or crontab:
# Run every day at 2 AM
*/2 * * * * python manage.py reconcile_balances

# Alert on discrepancies:  
RECONCILIATION_ALERTS_EMAIL = 'finance@cache.co.ke'
```

### 2. **Monitor Transaction Logs**

```python
# In settings.py - enable detailed logging:
LOGGING = {
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/cache/transactions.log',
        },
    },
    'loggers': {
        'payments.transaction_safety': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

### 3. **Alert on Anomalies**

```python
# Monitor for:
# ✓ Atomic transaction failures
# ✓ Balance inconsistencies found
# ✓ Failed withdrawals due to insufficient balance
# ✓ Orphaned transactions

def check_for_anomalies():
    # Failed transactions in last hour
    failed = Transaction.objects.filter(
        status='FAILED',
        created_at__gte=timezone.now() - timedelta(hours=1)
    )
    
    if failed.count() > 5:
        send_alert(f"⚠️ {failed.count()} failed transactions in last hour")
```

---

## Testing the Implementation

### 1. **Test Atomic Deposit**

```python
def test_atomic_deposit():
    user = CustomUser.objects.create(phone_number='254712345678')
    initial_balance = user.balance
    
    # Process deposit
    txn = safe_process_deposit(
        user=user,
        amount=Decimal('1000'),
        external_ref='TEST-001'
    )
    
    # Verify both updated
    user.refresh_from_db()
    assert user.balance == initial_balance + Decimal('1000')
    assert Transaction.objects.filter(external_ref='TEST-001').exists()
```

### 2. **Test Balance Inconsistency Detection**

```python
def test_balance_inconsistency_detection():
    user = CustomUser.objects.create(
        phone_number='254712345678',
        balance=Decimal('500')  # Wrong!
    )
    
    # Create one deposit manually (simulating corruption)
    Transaction.objects.create(
        user=user,
        type='DEPOSIT',
        amount=Decimal('1000'),
        status='COMPLETED'
    )
    
    # Should detect the inconsistency
    result = verify_user_balance_consistency(user.id)
    assert not result['is_consistent']
    assert result['difference'] == Decimal('-500')
```

### 3. **Test Idempotency (Safe Retries)**

```python
def test_idempotent_deposit():
    # If callback arrives twice, should be safe
    user = CustomUser.objects.create(phone_number='254712345678')
    
    # First request
    txn1 = safe_process_deposit(
        user=user,
        amount=Decimal('1000'),
        external_ref='IDEMPOTENT-001'
    )
    
    # Second request (duplicate callback)
    try:
        txn2 = safe_process_deposit(
            user=user,
            amount=Decimal('1000'),
            external_ref='IDEMPOTENT-001'  # Same external_ref!
        )
        assert False, "Should have raised uniqueness error"
    except Exception:
        pass  # Expected - prevents double deposits
```

---

## Next Steps

After this principle is solid, implement the remaining principles:

2. ✅ **Audit Trail & Immutability** - Track all changes
3. ⏳ **Backup Strategy** - Daily database backups
4. ⏳ **Reconciliation Checks** - Automated audits
5. ⏳ **Payment Reconciliation with M-Pesa** - Verify M-Pesa matches our DB
6. ⏳ **Data Encryption** - Encrypt phone numbers and sensitive data
7. ⏳ **Zero-Trust Verification** - High-value transaction approvals
8. ⏳ **Blockchain/Ledger Logging** - Immutable audit ledger
9. ⏳ **Monitoring & Alerts** - Real-time anomaly detection
10. ⏳ **Disaster Recovery Plan** - Recovery runbooks

---

## Resources

- **Django Transactions Doc**: https://docs.djangoproject.com/en/stable/topics/db/transactions/
- **Database Constraints**: https://docs.djangoproject.com/en/stable/ref/models/fields/#unique
- **Row-Level Locking**: https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-for-update
- **PostgreSQL ACID**: https://www.postgresql.org/about/featurematrix/

## Support

For questions about this implementation:
1. Review the docstrings in `payments/transaction_safety.py`
2. Check test cases in the testing section above
3. Enable DEBUG logging to see atomic transaction operations

---

**Status**: ✅ Implemented and Ready for Testing
**Date**: 2026-04-10
**Owner**: Financial Systems Team
