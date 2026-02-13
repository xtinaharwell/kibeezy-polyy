import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .utils import MpesaClient
from .models import Transaction

@csrf_exempt
def initiate_stk_push(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
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
                Transaction.objects.create(
                    user=request.user,
                    amount=amount,
                    phone_number=phone_number,
                    checkout_request_id=response.get('CheckoutRequestID'),
                    merchant_request_id=response.get('MerchantRequestID'),
                    status='PENDING'
                )
                return JsonResponse({'message': 'STK Push initiated successfully', 'checkout_id': response.get('CheckoutRequestID')})
            else:
                return JsonResponse({'error': response.get('CustomerMessage', 'Failed to initiate STK Push')}, status=400)
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def mpesa_callback(request):
    # This endpoint receives response from Safaricom
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            stk_callback = data.get('Body', {}).get('stkCallback', {})
            result_code = stk_callback.get('ResultCode')
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            
            transaction = Transaction.objects.get(checkout_request_id=checkout_request_id)
            
            if result_code == 0:
                transaction.status = 'COMPLETED'
            else:
                transaction.status = 'FAILED'
                
            transaction.save()
            return JsonResponse({'message': 'Callback processed'})
        except Transaction.DoesNotExist:
            return JsonResponse({'error': 'Transaction not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Method not allowed'}, status=405)
