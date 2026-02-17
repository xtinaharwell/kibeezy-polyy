import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from decimal import Decimal
from .mpesa_integration import get_mpesa_client
from .models import Transaction
from api.validators import validate_amount, ValidationError
from users.models import CustomUser

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["GET"])
def test_mpesa_credentials(request):
    """Test if M-Pesa credentials are valid"""
    try:
        client = get_mpesa_client()
        token = client.get_access_token()
        
        if token:
            return JsonResponse({
                'status': 'success',
                'message': 'M-Pesa credentials are valid',
                'token': token[:20] + '...'  # Show first 20 chars only
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to get access token'
            }, status=400)
    except Exception as e:
        logger.error(f"Credential test error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Credential validation failed: {str(e)}'
        }, status=400)

def get_authenticated_user(request):
    """Get authenticated user from session or X-User-Phone-Number header"""
    # Try session-based auth first
    if request.user and request.user.is_authenticated:
        return request.user
    
    # Fall back to header-based auth
    phone_number = request.headers.get('X-User-Phone-Number')
    if phone_number:
        try:
            return CustomUser.objects.get(phone_number=phone_number)
        except CustomUser.DoesNotExist:
            return None
    
    return None



@csrf_exempt
@require_http_methods(["POST"])
def initiate_stk_push(request):
    # Get authenticated user from session or header
    user = get_authenticated_user(request)
    if not user:
        logger.warning(f"Unauthorized STK push attempt")
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # TODO: Add KYC verification check once onboarding flow is ready
    # For now, allow all authenticated users to make deposits
    
    try:
        data = json.loads(request.body)
        amount = data.get('amount')
        
        # Validate amount using validators
        if not amount:
            return JsonResponse({'error': 'Amount is required'}, status=400)
        
        try:
            amount = validate_amount(amount, min_amount=Decimal('1'), max_amount=Decimal('150000'))
        except ValidationError as e:
            return JsonResponse({'error': e.message}, status=400)
        
        # Get M-Pesa client (real or mock)
        client = get_mpesa_client()
        
        # Initiate STK push
        response = client.initiate_stk_push(
            user.phone_number,
            amount,
            account_reference=f"KIBEEZY_{user.id}"
        )
        
        if response.get('ResponseCode') == '0':
            # Create a pending transaction
            transaction = Transaction.objects.create(
                user=user,
                type='DEPOSIT',
                amount=amount,
                phone_number=user.phone_number,
                checkout_request_id=response.get('CheckoutRequestID'),
                merchant_request_id=response.get('MerchantRequestID'),
                status='PENDING',
                description=f'M-Pesa deposit of KSH {amount}'
            )
            
            logger.info(f"STK Push initiated for user {user.phone_number}, amount: {amount}")
            return JsonResponse({
                'message': 'STK Push initiated successfully',
                'checkout_id': response.get('CheckoutRequestID'),
                'transaction_id': transaction.id,
                'customer_message': response.get('CustomerMessage', 'Check your phone for M-Pesa prompt')
            })
        else:
            return JsonResponse({
                'error': response.get('ResponseDescription', 'Failed to initiate STK Push'),
                'customer_message': response.get('CustomerMessage', 'Payment initiation failed')
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ValidationError as e:
        return JsonResponse({'error': e.message}, status=400)
    except Exception as e:
        logger.error(f"STK Push error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def b2c_result_callback(request):
    """
    Handle B2C result callback from M-Pesa Daraja API
    
    Safaricom will POST result to ResultURL with callback containing:
    - Result (0 = success)
    - ResultCode (0 = success)
    - OriginatorConversationID or ExternalReference (to match transaction)
    - ResponseDescription
    - ConversationID
    
    Flow:
    1. Parse callback data
    2. Find matching Transaction by external_ref or conversation_id
    3. If success: mark COMPLETED and credit user wallet
    4. If failed: mark FAILED and optionally retry
    5. Respond with 200 OK to Daraja
    """
    import logging
    from django.db import transaction as db_transaction
    
    logger = logging.getLogger(__name__)
    
    try:
        data = json.loads(request.body)
        logger.info(f"B2C callback received: {json.dumps(data)}")
        
        # Extract key fields from callback
        # Daraja may send different field names in Result and in timeout callback
        result_code = data.get('Result', {}).get('ResultCode') or data.get('ResultCode')
        external_ref = (
            data.get('Result', {}).get('ExternalReference') or 
            data.get('ExternalReference') or
            data.get('MerchantRequestID')
        )
        conversation_id = (
            data.get('Result', {}).get('ConversationID') or 
            data.get('ConversationID') or
            data.get('OriginatorConversationID')
        )
        response_description = (
            data.get('Result', {}).get('ResponseDescription') or 
            data.get('ResponseDescription', 'No description')
        )
        
        if not external_ref and not conversation_id:
            logger.warning(f"B2C callback missing identifiers: {data}")
            return JsonResponse({'status': 'error', 'message': 'Missing identifiers'}, status=400)
        
        # Find transaction by external_ref or conversation_id
        tx = None
        try:
            if external_ref:
                tx = Transaction.objects.get(external_ref=external_ref)
            elif conversation_id:
                # Search in mpesa_response JSON for matching conversation_id
                tx = Transaction.objects.filter(
                    mpesa_response__contains={'conversation_id': conversation_id}
                ).first()
        except Transaction.DoesNotExist:
            logger.warning(f"Transaction not found for external_ref={external_ref}, conv_id={conversation_id}")
            # Still respond 200 OK so Daraja doesn't keep retrying
            return JsonResponse({'status': 'error', 'message': 'transaction_not_found'})
        
        if not tx:
            logger.warning(f"No transaction found for callback: {external_ref or conversation_id}")
            return JsonResponse({'status': 'error', 'message': 'transaction_not_found'})
        
        # Check result code (0 = success)
        is_success = result_code == 0 or result_code == '0'
        
        with db_transaction.atomic():
            # Idempotency: check if already processed
            if tx.status == Transaction.COMPLETED:
                logger.info(f"Transaction {tx.id} already marked COMPLETED, skipping")
                return JsonResponse({'status': 'ok', 'message': 'already_processed'})
            
            if is_success:
                # Payment successful
                logger.info(f"B2C payout success for transaction {tx.id}, recipient {tx.user.phone_number}")
                
                tx.status = Transaction.COMPLETED
                tx.mpesa_response = tx.mpesa_response or {}
                tx.mpesa_response.update({
                    'callback_success': True,
                    'callback_result_code': result_code,
                    'callback_description': response_description,
                    'callback_time': timezone.now().isoformat()
                })
                tx.save()
                
                # Credit user wallet immediately
                user = tx.user
                user.balance += tx.amount
                user.save()
                
                logger.info(
                    f"User {user.phone_number} credited KES {tx.amount}, "
                    f"new balance: {user.balance}"
                )
                
                # Send notification (optional)
                _send_payout_notification(user, tx)
            
            else:
                # Payment failed
                logger.warning(
                    f"B2C payout failed for transaction {tx.id}, code={result_code}, "
                    f"description={response_description}"
                )
                
                tx.status = Transaction.FAILED
                tx.mpesa_response = tx.mpesa_response or {}
                tx.mpesa_response.update({
                    'callback_success': False,
                    'callback_result_code': result_code,
                    'callback_description': response_description,
                    'callback_time': timezone.now().isoformat()
                })
                tx.save()
                
                # Log for manual review / retry
                logger.error(
                    f"Payout failed: tx_id={tx.id}, user={tx.user.phone_number}, "
                    f"amount={tx.amount}, code={result_code}"
                )
        
        # Always respond 200 OK to Daraja
        return JsonResponse({'status': 'ok'}, status=200)
    
    except json.JSONDecodeError:
        logger.error("B2C callback: invalid JSON")
        return JsonResponse({'error': 'invalid_json'}, status=400)
    except Exception as e:
        logger.error(f"B2C callback processing error: {e}", exc_info=True)
        # Still return 200 to prevent Daraja retries
        return JsonResponse({'status': 'error', 'message': str(e)}, status=200)


def _send_payout_notification(user, transaction):
    """
    Send user a notification of successful payout (SMS, in-app, etc)
    (Placeholder for future notification system)
    """
    # TODO: implement notification system
    # e.g., send SMS via Africastalking
    # e.g., create in-app notification record
    logger = logging.getLogger(__name__)
    logger.info(f"Payout notification: User {user.phone_number} received KES {transaction.amount}")


@ensure_csrf_cookie
@require_http_methods(["GET"])
def get_transaction_status(request, transaction_id):
    """Get the status of a transaction"""
    try:
        # Get authenticated user from session or header
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        try:
            transaction = Transaction.objects.get(id=transaction_id, user=user)
        except Transaction.DoesNotExist:
            return JsonResponse({'error': 'Transaction not found'}, status=404)
        
        return JsonResponse({
            'id': transaction.id,
            'status': transaction.status,
            'amount': float(transaction.amount),
            'type': transaction.type,
            'created_at': transaction.created_at.isoformat()
        })
    
    except Exception as e:
        logger.error(f"Transaction status error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def mpesa_callback(request):
    """Handle M-Pesa callback to update transaction and user balance"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Get M-Pesa client
            client = get_mpesa_client()
            
            # Validate and process callback
            result = client.validate_callback(data)
            
            if not result:
                return JsonResponse({'error': 'Invalid callback data'}, status=400)
            
            checkout_request_id = result.get('checkout_request_id')
            
            try:
                transaction = Transaction.objects.get(checkout_request_id=checkout_request_id)
            except Transaction.DoesNotExist:
                logger.warning(f"Transaction not found for checkout_request_id: {checkout_request_id}")
                return JsonResponse({'error': 'Transaction not found'}, status=404)
            
            if result.get('status') == 'COMPLETED':
                # Payment successful
                transaction.status = 'COMPLETED'
                transaction.receipt_number = result.get('receipt_number')
                transaction.save()
                
                # Update user balance
                user = transaction.user
                user.balance += transaction.amount
                user.save()
                
                logger.info(f"Payment successful for user {user.phone_number}, new balance: {user.balance}")
            else:
                # Payment failed
                transaction.status = 'FAILED'
                transaction.save()
                logger.warning(f"Payment failed for transaction {transaction.id}")
                
            return JsonResponse({'message': 'Callback processed'})
        
        except Exception as e:
            logger.error(f"Callback processing error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)
