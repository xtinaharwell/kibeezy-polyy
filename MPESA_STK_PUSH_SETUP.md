# M-Pesa STK Push Integration Setup Guide

Your app is now configured for M-Pesa STK Push deposits. Here's how to set it up and test it.

## 1. Environment Configuration

Update your `.env` file with the following M-Pesa credentials:

```
# M-Pesa Configuration
MPESA_CONSUMER_KEY=ge4Xag54UcjJdXVWVmGu0LDsGKewSwucG6rorRTS4zGIrUkD
MPESA_CONSUMER_SECRET=VwrwIGOtihZTbWqA34R6EnB9Zlr6I8X3zGybQ6I3vEqcW4F2KvcutvDbAkPFuvHI
MPESA_SHORTCODE=174379
MPESA_PASSKEY=bfb279f9aa9bdbcf158e97dd1a2eda11571013d91c716d06
MPESA_CALLBACK_URL=https://yourdomain.com/api/payments/callback/
MPESA_DEBUG=False  # Set to True for mock testing, False for real transactions
```

### Where to Get These Credentials:

1. **Consumer Key & Secret**: Get from [Daraja API Portal](https://developer.safaricom.co.ke/)
   - Log in with your M-Pesa Business Account
   - Go to "My Applications"
   - Create a new app (if not already created)
   - Copy Consumer Key and Consumer Secret

2. **Shortcode**: Your M-Pesa Business Till/Paybill number (174379 is Safaricom's test shortcode)

3. **Passkey**: Get from the Daraja Portal under your app settings (STK Push Passkey)

4. **Callback URL**: This is the endpoint where M-Pesa sends payment confirmations
   - In development: Can use ngrok or localhost tunneling
   - In production: Use your actual domain (e.g., `https://kibeezy.com/api/payments/callback/`)

## 2. Testing in Development

### Option A: Mock Mode (No Real M-Pesa)
For testing without actually charging money, set in `.env`:
```
MPESA_DEBUG=True
```

This uses a mock M-Pesa client that simulates the payment flow.

### Option B: Sandbox Mode (Real Daraja API)
For testing with real M-Pesa Sandbox:

1. Set `MPESA_DEBUG=False` in `.env`
2. Use Safaricom's test phone number: `254712345678`
3. Test PIN: `123456`
4. Test amount: 1-150,000 KES

## 3. API Endpoints

### Initiate STK Push (Deposit)
```bash
POST /api/payments/stk-push/
Content-Type: application/json
Authorization: Your Auth Token or Session

{
    "amount": 500
}
```

**Response (Success):**
```json
{
    "message": "STK Push initiated successfully",
    "checkout_id": "ws_CO_DMZ_123456789",
    "transaction_id": 123,
    "customer_message": "Check your phone for M-Pesa prompt"
}
```

**Response (Error):**
```json
{
    "error": "Invalid amount",
    "customer_message": "Amount must be between 1 and 150,000 KES"
}
```

### Handle Callbacks
M-Pesa will POST to your callback URL when payment is completed:
```
POST /api/payments/callback/
```

The callback handler will:
1. Verify the payment was successful
2. Update the transaction status to COMPLETED
3. Credit the user's wallet immediately
4. Return 200 OK to M-Pesa

## 4. Flow Diagram

```
User clicks "Deposit" 
    ↓
DepositModal opens (frontend)
    ↓
User enters amount and submits
    ↓
Frontend calls POST /api/payments/stk-push/
    ↓
Backend creates pending Transaction
    ↓
Backend calls M-Pesa Daraja API (initiate_stk_push)
    ↓
M-Pesa sends STK prompt to user's phone
    ↓
User enters M-Pesa PIN on phone
    ↓
M-Pesa processes payment
    ↓
M-Pesa sends callback to /api/payments/callback/
    ↓
Backend marks Transaction as COMPLETED
    ↓
Backend credits user's wallet
    ↓
User sees success message
```

## 5. Database Schema

The `Transaction` model stores deposit records:

```python
Transaction(
    user=User,           # The user making the deposit
    type='DEPOSIT',      # Transaction type
    amount=500,          # Amount in KES
    phone_number='254712345678',  # M-Pesa phone number
    checkout_request_id='ws_CO_DMZ_...',  # M-Pesa reference
    merchant_request_id='txn_123...',     # Merchant reference
    status='PENDING' | 'COMPLETED' | 'FAILED',
    description='M-Pesa deposit of KSH 500',
    created_at=datetime,
    updated_at=datetime
)
```

## 6. Testing the Integration

### Via Frontend (Recommended)
1. Start Django backend: `python manage.py runserver`
2. Start Next.js frontend: `npm run dev`
3. Log in to the app
4. Click "Deposit" button
5. Enter amount (e.g., 100 KES)
6. Click "Deposit" button in modal

**In Mock Mode:** You'll see success immediately
**In Sandbox Mode:** M-Pesa prompt will appear on the test phone

### Via cURL (API Testing)
```bash
curl -X POST http://localhost:8000/api/payments/stk-push/ \
  -H "Content-Type: application/json" \
  -H "X-User-Phone-Number: 254712345678" \
  -d '{"amount": 500}'
```

## 7. Production Setup

Before going live with real payments:

1. **Switch to Production Daraja API:**
   - Update `base_url` in `mpesa_integration.py` from sandbox to production
   - Get real Consumer Key/Secret from Daraja Portal

2. **Update Callback URL:**
   ```
   MPESA_CALLBACK_URL=https://yourdomain.com/api/payments/callback/
   ```

3. **Database Migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Set Debug to False:**
   ```
   DEBUG=False
   MPESA_DEBUG=False
   ```

5. **Configure KYC Verification:**
   - Ensure users are KYC-verified before allowing deposits
   - Uncomment KYC check in `payments/views.py`

6. **Enable HTTPS:**
   ```
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   ```

## 8. Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `Invalid phone number format` | Phone number not in format 254xxxxxxxxx | Ensure phone starts with 254 |
| `Invalid amount` | Amount < 1 or > 150,000 | Use amount between 1-150,000 |
| `Failed authentication` | Consumer Key/Secret wrong | Verify in Daraja Portal |
| `MaxClientsInSessionMode reached` | Too many concurrent connections | See database connection pooling guide |
| `Callback not received` | Callback URL not accessible | Use ngrok or expose localhost to internet |

## 9. Security Considerations

✅ **Implemented:**
- CSRF protection on sensitive endpoints
- Authentication required for deposits
- Amount validation (min/max)
- Phone number format validation
- Timestamp-based password generation
- Base64 encoding of credentials

⚠️ **To Add:**
- Rate limiting on STK Push endpoint (prevent spam)
- Idempotency keys for duplicate request handling
- Transaction signing/verification
- KYC verification requirement
- Fraud detection system

## 10. Code Files

Key files involved in the STK Push flow:

- `payments/mpesa_integration.py` - M-Pesa API integration class
- `payments/views.py` - Django views for endpoints
- `payments/urls.py` - URL routing
- `payments/models.py` - Transaction model
- `kibeezy-poly/components/DepositModal.tsx` - Frontend deposit UI
- `kibeezy-poly/lib/fetchWithAuth.ts` - API client utility

## 11. Monitoring & Logging

Check logs for payment transactions:

```bash
# View recent deposits
python manage.py dbshell
SELECT * FROM payments_transaction WHERE type='DEPOSIT' ORDER BY created_at DESC LIMIT 10;

# View failed transactions
SELECT * FROM payments_transaction WHERE status='FAILED';
```

In production, configure proper logging service (e.g., Sentry, LogRocket).

## 12. Testing Checklist

- [ ] Environment variables configured correctly
- [ ] Django server running without errors
- [ ] Frontend DepositModal appears
- [ ] Can enter deposit amount
- [ ] STK Push endpoint returns success response
- [ ] M-Pesa prompt appears (in Sandbox mode)
- [ ] Payment confirmed updates user balance
- [ ] Transaction shows in database
- [ ] Callback URL receives and processes callback
- [ ] Error messages display properly

## Questions or Issues?

Refer to:
- Safaricom Daraja API Docs: https://developer.safaricom.co.ke/docs
- Django REST Framework: https://www.django-rest-framework.org/
- M-Pesa Test Credentials: [Daraja Portal](https://developer.safaricom.co.ke/)
