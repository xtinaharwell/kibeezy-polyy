"""
SECURITY IMPLEMENTATION GUIDE
How to apply rate limiting, audit logging, and input validation to your endpoints

This file shows best practices and examples for securing critical endpoints.
Apply these patterns to your existing views.
"""

# ============================================================================
# EXAMPLE 1: PLACE BET ENDPOINT (Markets)
# ============================================================================

"""
BEFORE (Vulnerable):
@csrf_exempt
@require_http_methods(['POST'])
def place_bet(request):
    data = json.loads(request.body)
    amount = data.get('amount')  # No validation
    outcome = data.get('outcome')  # No validation
    market_id = data.get('market_id')  # No validation
    
    # Direct database access - potential SQL injection
    bet = Bet.objects.create(
        user=user,
        amount=amount,
        outcome=outcome,
        market_id=market_id
    )
    
    user.balance -= amount
    user.save()  # No audit trail
    
    return JsonResponse({'status': 'success'})


AFTER (Secure):
"""
from api.rate_limiting import rate_limit, get_client_context
from api.audit_logging import AuditLogger
from api.validators import validate_amount, validate_bet_outcome, ValidationError

@rate_limit(max_requests=50, window_seconds=3600)  # 50 bets per hour
@require_http_methods(['POST'])
def place_bet_secure(request):
    try:
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)
        
        # Parse request data
        data = json.loads(request.body)
        
        # 1. INPUT VALIDATION (SQL Injection prevention + XSS)
        try:
            amount = validate_amount(data.get('amount'))
            outcome = validate_bet_outcome(data.get('outcome'))
            market_id = int(data.get('market_id'))  # Validate as integer
        except (ValidationError, ValueError, TypeError) as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Invalid input: {str(e)}'
            }, status=400)
        
        # 2. BUSINESS LOGIC VALIDATION
        if amount > user.balance:
            return JsonResponse({
                'status': 'error',
                'message': f'Insufficient balance. Current: {user.balance}'
            }, status=400)
        
        # 3. FETCH WITH VALIDATED PARAMETERS (Django ORM prevents SQL injection)
        try:
            market = Market.objects.get(id=market_id)
        except Market.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Market not found'}, status=404)
        
        if market.status != 'OPEN':
            return JsonResponse({'status': 'error', 'message': 'Market is not open'}, status=400)
        
        # 4. CREATE BET WITH AUDIT TRAIL
        try:
            bet = Bet.objects.create(
                user=user,
                market=market,
                amount=amount,
                outcome=outcome,
                entry_probability=market.yes_probability
            )
            
            # 5. LOG FINANCIAL TRANSACTION
            ip_address, user_agent = get_client_context(request)
            AuditLogger.log_bet_placed(user, bet, market, amount, ip_address, user_agent)
            
            # Update user balance
            user.balance = user.balance - amount
            user.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Bet placed successfully',
                'bet_id': bet.id,
                'new_balance': str(user.balance)
            })
        
        except Exception as e:
            logger.error(f"Error placing bet: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to place bet'
            }, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)


# ============================================================================
# EXAMPLE 2: DEPOSIT/PAYMENT ENDPOINT (Payments)
# ============================================================================

from api.rate_limiting import rate_limit_payments
from api.validators import validate_phone_number

@rate_limit_payments  # 10 payments per hour
@require_http_methods(['POST'])
def initiate_stk_push_secure(request):
    try:
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)
        
        data = json.loads(request.body)
        
        # 1. INPUT VALIDATION
        try:
            phone_number = validate_phone_number(data.get('phone_number'))
            amount = validate_amount(data.get('amount'), min_amount=Decimal('1'), max_amount=Decimal('150000'))
        except ValidationError as e:
            return JsonResponse({'status': 'error', 'message': str(e.message)}, status=400)
        
        # 2. BUSINESS LOGIC VALIDATION
        if amount < Decimal('1') or amount > Decimal('150000'):
            return JsonResponse({'status': 'error', 'message': 'Amount out of range'}, status=400)
        
        # 3. RATE LIMITING CHECK (already done by decorator)
        
        # 4. CREATE TRANSACTION RECORD (for audit)
        try:
            transaction = Transaction.objects.create(
                user=user,
                type='DEPOSIT',
                amount=amount,
                phone_number=phone_number,
                status='PENDING'
            )
            
            # 5. CALL MPESA API
            client = get_mpesa_client()
            checkout_request_id = client.stk_push(
                phone_number=phone_number,
                amount=int(amount),
                account_ref=f"cache-{transaction.id}"
            )
            
            # 6. UPDATE TRANSACTION & LOG
            transaction.checkout_request_id = checkout_request_id
            transaction.save()
            
            ip_address, user_agent = get_client_context(request)
            AuditLogger.log_financial_transaction(
                action='DEPOSIT_INITIATED',
                user=user,
                amount=amount,
                content_type='payments.Transaction',
                object_id=transaction.id,
                description=f'STK Push initiated for {amount} KES',
                ip_address=ip_address,
                user_agent=user_agent,
                severity='MEDIUM'
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'STK Push sent. Enter PIN on your phone.',
                'checkout_request_id': checkout_request_id
            })
        
        except Exception as e:
            logger.error(f"STK Push error: {str(e)}")
            ip_address, user_agent = get_client_context(request)
            AuditLogger.log_security_event(
                action='DEPOSIT_FAILED',
                user=user,
                description=f'Deposit initiation failed: {str(e)}',
                ip_address=ip_address,
                user_agent=user_agent,
                severity='MEDIUM'
            )
            return JsonResponse({'status': 'error', 'message': 'Failed to initiate payment'}, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)


# ============================================================================
# EXAMPLE 3: USER REGISTRATION (Auth)
# ============================================================================

from api.rate_limiting import rate_limit_auth_attempts
from api.validators import validate_full_name, validate_phone_number

@rate_limit_auth_attempts  # 5 attempts per 15 minutes
@require_http_methods(['POST'])
def signup_secure(request):
    try:
        data = json.loads(request.body)
        
        # 1. INPUT VALIDATION & SANITIZATION
        try:
            phone_number = validate_phone_number(data.get('phone_number'))
            full_name = validate_full_name(data.get('full_name'))
            pin = data.get('pin')
            
            if not pin or len(pin) < 4:
                raise ValidationError('PIN must be at least 4 digits')
        
        except ValidationError as e:
            ip_address, user_agent = get_client_context(request)
            AuditLogger.log_security_event(
                action='SIGNUP_VALIDATION_FAILED',
                user=None,
                description=f'Signup validation failed: {str(e.message)}',
                ip_address=ip_address,
                user_agent=user_agent,
                severity='LOW'
            )
            return JsonResponse({'status': 'error', 'message': str(e.message)}, status=400)
        
        # 2. CHECK FOR DUPLICATES (uses Django ORM - safe from SQL injection)
        if CustomUser.objects.filter(phone_number=phone_number).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Phone number already registered'
            }, status=400)
        
        # 3. CREATE USER
        try:
            user = CustomUser.objects.create_user(
                phone_number=phone_number,
                full_name=full_name,
                password=pin
            )
            
            # 4. LOG AUDIT TRAIL
            ip_address, user_agent = get_client_context(request)
            AuditLogger.log_financial_transaction(
                action='USER_REGISTERED',
                user=user,
                amount=0,
                content_type='users.CustomUser',
                object_id=user.id,
                description=f'New user registered',
                ip_address=ip_address,
                user_agent=user_agent,
                severity='MEDIUM'
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'User created successfully',
                'user_id': user.id
            })
        
        except Exception as e:
            logger.error(f"User creation error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Failed to create user'}, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)


# ============================================================================
# QUICK REFERENCE: Security Checklist for Every Endpoint
# ============================================================================

"""
✓ 1. Authentication & Authorization
   - Check user is authenticated
   - Check user has required permissions
   - Use get_authenticated_user(request)

✓ 2. Rate Limiting
   - Apply @rate_limit decorator for expensive operations
   - Use @rate_limit_payments for payment endpoints
   - Use @rate_limit_auth_attempts for auth endpoints

✓ 3. Input Validation
   - Use validators from api.validators
   - Validate data types, ranges, and formats
   - Never trust user input

✓ 4. SQL Injection Prevention
   - Always use Django ORM (Queryset)
   - Never use raw SQL with string interpolation
   - Use parameterized queries if raw SQL necessary

✓ 5. XSS Prevention
   - Use sanitize_user_input() for user-submitted text
   - React automatically escapes text (unless dangerouslySetInnerHTML)
   - Never use dangerouslySetInnerHTML with user content

✓ 6. Audit Logging
   - Log all financial transactions with AuditLogger
   - Log security events (failed auth, rate limits exceeded)
   - Include IP address and user agent

✓ 7. Error Handling
   - Don't expose technical details in error messages
   - Log full errors for debugging
   - Return generic error messages to clients

✓ 8. CSRF Protection
   - Use @csrf_exempt only when necessary and justified
   - Always include CSRF token in POST requests
   - Set appropriate cookie flags

✓ 9. HTTPS & TLS
   - Set SECURE_SSL_REDIRECT = True in production
   - Use HSTS headers
   - Enforce HTTPS for sensitive operations

✓ 10. Dependencies & Updates
   - Run `pip audit` to check for vulnerable packages
   - Keep Django and dependencies updated
   - Use dependency pinning in requirements.txt
"""
