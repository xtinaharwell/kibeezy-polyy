import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .utils import MpesaClient
from .models import Transaction

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def initiate_stk_push(request):
    logger.info(f"STK Push request - User: {request.user}, Is authenticated: {request.user.is_authenticated}")
    logger.info(f"Session: {request.session.session_key}, Cookies: {request.COOKIES}")
    
    # Check authentication first
    if not request.user or not request.user.is_authenticated:
        logger.warning(f"Unauthorized STK push attempt. User authenticated: {request.user.is_authenticated if request.user else 'No user'}")
        return JsonResponse({'error': 'Authentication required'}, status=401)
        
    try:
        data = json.loads(request.body)
        amount = data.get('amount')
        
        if not amount:
            return JsonResponse({'error': 'Amount is required'}, status=400)
        
        # The user's phone number from their profile
        phone_number = request.user.phone_number
        
        client = MpesaClient()
        # In production, use a real callback URL
        callback_url = "https://yourdomain.com/api/payments/callback/"
        
        response = client.stk_push(phone_number, amount, callback_url)
        
        if response.get('ResponseCode') == '0':
            # Create a pending transaction
            transaction = Transaction.objects.create(
                user=request.user,
                type='DEPOSIT',
                amount=Decimal(str(amount)),
                phone_number=phone_number,
                checkout_request_id=response.get('CheckoutRequestID'),
                merchant_request_id=response.get('MerchantRequestID'),
                status='PENDING',
                description=f'M-Pesa deposit of KSH {amount}'
            )
            
            logger.info(f"STK Push initiated for user {request.user.phone_number}, amount: {amount}")
            return JsonResponse({
                'message': 'STK Push initiated successfully', 
                'checkout_id': response.get('CheckoutRequestID'),
                'transaction_id': transaction.id
            })
        else:
            return JsonResponse({'error': response.get('CustomerMessage', 'Failed to initiate STK Push')}, status=400)
            
    except Exception as e:
        logger.error(f"STK Push error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def mpesa_callback(request):
    """Handle M-Pesa callback to update transaction and user balance"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            stk_callback = data.get('Body', {}).get('stkCallback', {})
            result_code = stk_callback.get('ResultCode')
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            
            try:
                transaction = Transaction.objects.get(checkout_request_id=checkout_request_id)
            except Transaction.DoesNotExist:
                logger.warning(f"Transaction not found for checkout_request_id: {checkout_request_id}")
                return JsonResponse({'error': 'Transaction not found'}, status=404)
            
            if result_code == 0:
                # Payment successful
                transaction.status = 'COMPLETED'
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
                logger.warning(f"Payment failed for transaction {transaction.id}, result_code: {result_code}")
                
            return JsonResponse({'message': 'Callback processed'})
        except Exception as e:
            logger.error(f"Callback error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Method not allowed'}, status=405)
