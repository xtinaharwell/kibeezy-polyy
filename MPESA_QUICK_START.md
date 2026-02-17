# M-Pesa STK Push - Quick Start

Your Kibeezy app is ready for M-Pesa deposits! Here's what's already set up:

## ✅ What's Ready

- **Backend**: M-Pesa STK Push integration (`payments/mpesa_integration.py`)
- **API Endpoints**: 
  - `POST /api/payments/stk-push/` - Initiate deposit
  - `POST /api/payments/callback/` - Receive M-Pesa confirmation
- **Frontend**: DepositModal component with form and API integration
- **Database**: Transaction model to track deposits
- **Two Modes**: Mock (for testing) and Real (for Sandbox/Production)

## 🚀 Quick Test (5 minutes)

### 1. Update `.env` file with M-Pesa credentials:

```bash
# Add to .env in kibeezy-polyy folder
MPESA_PASSKEY=bfb279f9aa9bdbcf158e97dd1a2eda11571013d91c716d06
MPESA_CALLBACK_URL=http://127.0.0.1:8000/api/payments/callback/
MPESA_DEBUG=True  # Use mock for testing, no real charges
```

> Get MPESA_PASSKEY from: https://developer.safaricom.co.ke/ (under your app's STK Push settings)

### 2. Start the servers

**Terminal 1 (Backend):**
```bash
cd kibeezy-polyy
python manage.py runserver 0.0.0.0:8000
```

**Terminal 2 (Frontend):**
```bash
cd kibeezy-poly
npm run dev
```

### 3. Test the deposit flow

1. Go to http://localhost:3000
2. Log in to your account
3. Go to **Dashboard**
4. Click **Deposit** button
5. Enter an amount (e.g., 500)
6. Click **Deposit KSh 500**

**Mock Mode Result:** You'll see success message immediately ✅

**Real Sandbox Mode Result:** M-Pesa prompt will appear on phone (use test number 254712345678)

## 📊 Check if it worked

After successful deposit:

1. **Check user balance** - Should increase by deposit amount
2. **Check database**:
   ```bash
   # In another terminal:
   cd kibeezy-polyy
   python manage.py shell
   >>> from payments.models import Transaction
   >>> Transaction.objects.filter(type='DEPOSIT').last()
   ```

3. **Check console logs** - Backend should log the whole flow

## 🔧 Configuration

### Current Setup in `.env.example`:
```
MPESA_CONSUMER_KEY=ge4Xag54UcjJdXVWVmGu0LDsGKewSwucG6rorRTS4zGIrUkD
MPESA_CONSUMER_SECRET=VwrwIGOtihZTbWqA34R6EnB9Zlr6I8X3zGybQ6I3vEqcW4F2KvcutvDbAkPFuvHI
MPESA_SHORTCODE=174379
MPESA_PASSKEY=<YOUR_PASSKEY_HERE>
MPESA_CALLBACK_URL=http://127.0.0.1:8000/api/payments/callback/
MPESA_DEBUG=True
```

### To Switch to Real Sandbox:
1. Set `MPESA_DEBUG=False`
2. Use test phone: `254712345678`
3. Test PIN: `123456`
4. Safaricom will charge a small test amount (usually 1-10 KES)

### To Switch to Production:
1. Get real Consumer Key/Secret from Daraja (not sandbox)
2. Update MPESA_SHORTCODE to your actual paybill number
3. Update MPESA_CALLBACK_URL to your production domain
4. Set `MPESA_DEBUG=False`
5. Set `DEBUG=False` in Django settings

## 📝 Code Overview

### Frontend (Deposit Modal)
```typescript
// kibeezy-poly/components/DepositModal.tsx
- Collects amount from user
- Calls: POST /api/payments/stk-push/ with { amount }
- Shows processing/success states
```

### Backend (STK Push)
```python
# kibeezy-polyy/payments/views.py
def initiate_stk_push(request):
    - Validates user authentication
    - Validates amount (1-150,000 KES)
    - Calls M-Pesa API to initiate STK push
    - Creates pending Transaction in database
    - Returns checkout_id to frontend
```

### M-Pesa Callback
```python
# kibeezy-polyy/payments/views.py
def mpesa_callback(request):
    - Receives POST from M-Pesa when payment completes
    - Validates payment status
    - If successful: marks Transaction as COMPLETED
    - Credits user's wallet immediately
    - Returns 200 OK to M-Pesa
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Connection refused to backend" | Make sure `npm run dev` is running in kibeezy-poly folder |
| "Authentication required" | Make sure you're logged in before clicking Deposit |
| "Invalid amount" | Use amount between 100-150,000 KES |
| Callback not received | Set `MPESA_CALLBACK_URL=http://127.0.0.1:8000/api/payments/callback/` |
| "MPESA_PASSKEY not set" | Add to `.env` file in kibeezy-polyy folder |

## 📚 Full Documentation

See `MPESA_STK_PUSH_SETUP.md` for:
- Detailed environment setup
- Getting real M-Pesa credentials
- Production deployment steps
- Security considerations
- Error handling
- Database schema
- API endpoint details

## ✨ What Happens Behind the Scenes

```
User submits form
    ↓
Frontend: POST /api/payments/stk-push/ with amount
    ↓
Backend: Creates pending Transaction
    ↓
Backend: Calls M-Pesa Daraja API
    ↓
M-Pesa: Sends STK prompt to user's phone
    ↓
User: Enters M-Pesa PIN
    ↓
M-Pesa: Processes payment
    ↓
M-Pesa: Sends callback to /api/payments/callback/
    ↓
Backend: Marks Transaction as COMPLETED
    ↓
Backend: Adds amount to user.balance
    ↓
Frontend: Shows success message
    ↓
Dashboard: Balance updated instantly
```

## 🎯 Next Steps

1. ✅ Add MPESA_PASSKEY to .env
2. ✅ Run backend and frontend
3. ✅ Test full deposit flow
4. ⏭️ Add withdrawal feature (reverse flow)
5. ⏭️ Add transaction history UI
6. ⏭️ Add payment receipt/confirmation emails

---

**Ready to test?** Run the servers and hit the Deposit button! 🚀
