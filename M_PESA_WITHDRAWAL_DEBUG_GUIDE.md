# M-Pesa Withdrawal Status Fix - Debugging Guide

## Problem Summary

M-Pesa withdrawals were staying in PENDING status even after successful payment because:

1. **Bug**: Undefined variable `user` in callback handler (line 348 in views.py) → callback processing crashed
2. **No status polling**: No way to manually check if callback was received
3. **Poor logging**: Difficult to debug transaction matching issues
4. **Callback matching**: Transaction lookup could fail if field names didn't match

## Fixes Applied

### 1. ✅ Fixed Undefined Variable Bug
**File**: `payments/views.py` (line 348)

**Before**:
```python
_send_payout_notification(user, tx)  # ❌ 'user' undefined
```

**After**:
```python
_send_payout_notification(tx.user, tx)  # ✅ Fixed
```

### 2. ✅ Added Manual Status Sync Endpoint
**New Endpoint**: `/api/payments/withdraw/sync/`

**Purpose**: Manually check withdrawal status if callback is delayed or failed.

**Request**:
```bash
POST /api/payments/withdraw/sync/
{
  "transaction_id": 123
}
```

**Response**:
```json
{
  "status": "PENDING" | "COMPLETED" | "FAILED",
  "amount": 500.00,
  "message": "...",
  "external_ref": "600000_20260416...",
  "checkout_request_id": "...",
  "created_at": "2026-04-16T10:30:00Z",
  "last_updated": "2026-04-16T10:30:05Z"
}
```

### 3. ✅ Enhanced Callback Logging
The callback handler now logs:
- Exact callback payload received
- All extracted fields (ResultCode, ConversationID, OriginatorConversationID)
- Each transaction lookup attempt
- Where the transaction was found
- Success/failure with detailed messages

### 4. ✅ Improved Transaction Matching
The callback handler now tries multiple lookup methods:

1. **Method 1**: By `external_ref`
2. **Method 2**: By `checkout_request_id` (stores OriginatorConversationID)
3. **Method 3**: By `merchant_request_id` (stores ConversationID)
4. **Method 4**: By JSON search in `mpesa_response`

---

## How M-Pesa B2C Works

```
User Requests Withdrawal
       ↓
Call B2C API → Immediate Acknowledgment (ResponseCode=0)
       ↓
B2C request queued on M-Pesa servers
       ↓
(Async Processing on M-Pesa side)
       ↓
M-Pesa Callback → /api/payments/b2c-callback/
       ↓
Update Transaction: PENDING → COMPLETED/FAILED
       ↓
User sees updated status
```

**Key Point**: The initial B2C response is just an acknowledgment. The actual transaction result comes via async callback from M-Pesa.

---

## Troubleshooting

### Issue 1: Withdrawal Shows as PENDING but Money Was Received

**Likely Cause**: Callback was received and processed, but UI isn't refreshed.

**Fix**:
1. Frontend should poll `/api/payments/transaction/{id}/status/` every 5-10 seconds
2. Subscribe to real-time updates (websockets) if available
3. Call the new `/api/payments/withdraw/sync/` endpoint manually

### Issue 2: Callback Not Being Received at All

**Check These**:

1. **Callback URL is correct**:
   ```python
   # In settings or daraja_b2c.py
   CALLBACK_URL = getattr(settings, 'MPESA_CALLBACK_URL', 'https://CACHE.co.ke/api/payments/b2c-callback/')
   ```
   Verify this URL is publicly accessible and not behind auth.

2. **Endpoint is CSRF-exempt**:
   ```python
   @csrf_exempt  # ✅ Callback must be exempt
   @require_http_methods(["POST"])
   def b2c_result_callback(request):
   ```

3. **Logs to check**:
   ```bash
   # Check Django logs for callback receipt
   tail -f logs/django.log | grep "B2C callback"
   ```

4. **Test with curl** (to ensure endpoint is accessible):
   ```bash
   curl -X POST https://CACHE.co.ke/api/payments/b2c-callback/ \
     -H "Content-Type: application/json" \
     -d '{
       "Result": {
         "ResultCode": 0,
         "ResultDesc": "The service request has been processed successfully.",
         "OriginatorConversationID": "600000_20260416123456_abcd1234",
         "ConversationID": "AG_20260416_abc123def456",
         "TransactionID": "LIB123456789",
         "ResponseDescription": "The service request has been processed successfully."
       }
     }'
   ```

### Issue 3: Transaction Lookup Failing in Callback

**Symptoms**: Logs show "Transaction not found" despite withdrawal being initiated

**Check**:
1. Verify fields stored during withdrawal initiation:
   ```python
   # In initiate_withdrawal():
   transaction.merchant_request_id = response.get('ConversationID')      # ✅ ← Used by callback
   transaction.checkout_request_id = response.get('OriginatorConversationID')  # ✅ ← Used by callback
   ```

2. Check logs for which lookup method succeeded
3. If none work, callback payload field names might differ—check logs

### Issue 4: Balance Not Refunded After Failed Withdrawal

**Expected Behavior**:
- ✅ Withdrawal initiated → Balance deducted immediately
- ✅ Callback received: Success → Balance stays deducted (payment sent)
- ✅ Callback received: Failed → Balance refunded

**Check**:
1. Verify transaction status changed to FAILED
2. Check that user balance was restored:
   ```python
   # In b2c_result_callback when is_success=False:
   user.balance += tx.amount  # ✅ Must be done
   ```

---

## Testing Checklist

### Manual Test 1: Withdrawal Flow
```bash
# 1. Initiate withdrawal
curl -X POST http://localhost:8000/api/payments/withdraw/ \
  -H "X-User-Phone-Number: 254712345678" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100}'

# Response should include transaction_id
# {"transaction_id": 123, "status": "PENDING", ...}

# 2. Check status (should be PENDING)
curl http://localhost:8000/api/payments/transaction/123/status/ \
  -H "X-User-Phone-Number: 254712345678"

# 3. Simulate M-Pesa callback
curl -X POST http://localhost:8000/api/payments/b2c-callback/ \
  -H "Content-Type: application/json" \
  -d '{...}' # See mock callback below

# 4. Check status again (should be COMPLETED)
curl http://localhost:8000/api/payments/transaction/123/status/ \
  -H "X-User-Phone-Number: 254712345678"
```

### Mock Callback Payload (Success)
```json
{
  "Result": {
    "ResultCode": 0,
    "ResultDesc": "The service request has been processed successfully",
    "OriginatorConversationID": "600000_20260416123456_abcd1234",
    "ConversationID": "AG_20260416_abc123",
    "TransactionID": "LIB123456",
    "ResponseDescription": "Processed successfully"
  }
}
```

### Mock Callback Payload (Failure)
```json
{
  "Result": {
    "ResultCode": 1,
    "ResultDesc": "Insufficient balance",
    "OriginatorConversationID": "600000_20260416123456_abcd1234",
    "ConversationID": "AG_20260416_abc123",
    "ResponseDescription": "Insufficient balance"
  }
}
```

---

## Logs to Monitor

```bash
# Watch for callback receipts
tail -f logs/django.log | grep -i "b2c callback"

# Watch for transaction status updates
tail -f logs/django.log | grep -i "withdrawal"

# Watch for specific transaction
tail -f logs/django.log | grep "tx_id=123"

# Export logs for analysis
grep -i "b2c" logs/django.log > /tmp/b2c_debug.log
```

---

## New Endpoint Reference

### Sync Withdrawal Status
- **URL**: `/api/payments/withdraw/sync/`
- **Method**: POST
- **Auth**: Required (X-User-Phone-Number or session)
- **Purpose**: Manual check if callback was received (for UI polling)

**Request**:
```json
{
  "transaction_id": 123
}
```

**Response** (if PENDING):
```json
{
  "status": "PENDING",
  "amount": 500.00,
  "message": "Withdrawal is pending. M-Pesa will send status via callback.",
  "external_ref": "600000_20260416...",
  "checkout_request_id": "...",
  "created_at": "2026-04-16T10:30:00Z",
  "last_updated": "2026-04-16T10:30:05Z"
}
```

**Response** (if COMPLETED):
```json
{
  "status": "COMPLETED",
  "amount": 500.00,
  "message": "Withdrawal is COMPLETED",
  "mpesa_response": {...}
}
```

---

## Frontend Implementation

### React Component Example
```javascript
// Check withdrawal status with polling
const [status, setStatus] = useState('PENDING');
const [isChecking, setIsChecking] = useState(false);

const syncStatus = async (transactionId) => {
  setIsChecking(true);
  try {
    const res = await fetch(`/api/payments/withdraw/sync/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transaction_id: transactionId })
    });
    const data = await res.json();
    setStatus(data.status);
    
    if (data.status === 'PENDING') {
      // Keep polling
      setTimeout(() => syncStatus(transactionId), 5000);
    }
  } finally {
    setIsChecking(false);
  }
};

// Or use the transaction status endpoint
const checkTransactionStatus = async (transactionId) => {
  const res = await fetch(`/api/payments/transaction/${transactionId}/status/`);
  return await res.json();
};
```

---

## Summary

| Fix | Status | Impact |
|-----|--------|--------|
| Fix undefined `user` variable | ✅ Done | Callbacks won't crash anymore |
| Add status sync endpoint | ✅ Done | Users can check status manually |
| Improve callback logging | ✅ Done | Easy debugging |
| Better transaction matching | ✅ Done | Higher callback success rate |

**Next Step**: 
1. Deploy these changes
2. Monitor logs for any callback issues
3. Test with manual withdrawals
4. Update frontend to poll `/withdraw/sync/` or use the transaction status endpoint
