import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from decimal import Decimal
from .mpesa_integration import get_mpesa_client
from .models import Transaction
from api.validators import validate_amount, ValidationError

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def initiate_stk_push(request):
    # Check authentication
    if not request.user or not request.user.is_authenticated:
        logger.warning(f"Unauthorized STK push attempt")
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Check if user is KYC verified
    if not request.user.kyc_verified:
        return JsonResponse({
            'error': 'KYC verification required',
            'message': 'Please verify your phone number before making deposits'
        }, status=403)
    
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
            request.user.phone_number,
            amount,
            account_reference=f"KIBEEZY_{request.user.id}"
        )
        
        if response.get('ResponseCode') == '0':
            # Create a pending transaction
            transaction = Transaction.objects.create(
                user=request.user,
                type='DEPOSIT',
                amount=amount,
                phone_number=request.user.phone_number,
                checkout_request_id=response.get('CheckoutRequestID'),
                merchant_request_id=response.get('MerchantRequestID'),
                status='PENDING',
                description=f'M-Pesa deposit of KSH {amount}'
            )
            
            logger.info(f"STK Push initiated for user {request.user.phone_number}, amount: {amount}")
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


@ensure_csrf_cookie
@require_http_methods(["POST"])
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
