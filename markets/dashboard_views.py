import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from .models import Market, Bet
from payments.models import Transaction
from users.models import CustomUser

logger = logging.getLogger(__name__)

def get_authenticated_user(request):
    """
    Get authenticated user from either:
    1. Session (if session cookie exists)
    2. X-User-Phone-Number header (for development/CORS)
    """
    # First try session
    if request.user and request.user.is_authenticated:
        return request.user
    
    # Fallback to header-based authentication for development
    phone_number = request.headers.get('X-User-Phone-Number')
    if phone_number:
        try:
            user = CustomUser.objects.get(phone_number=phone_number)
            if user.is_active:
                return user
        except CustomUser.DoesNotExist:
            pass
    
    return None

@csrf_exempt
@require_http_methods(["GET"])
def user_dashboard(request):
    # Check authentication
    user = get_authenticated_user(request)
    if not user:
        logger.warning(f"Dashboard access denied - user not authenticated")
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    logger.info(f"Dashboard loaded for user: {user.phone_number}")
    
    try:
        
        # Get user bets with market info
        bets = Bet.objects.filter(user=user).select_related('market').order_by('-timestamp')
        
        bets_data = []
        portfolio_value = Decimal('0.00')
        
        for bet in bets:
            bets_data.append({
                'id': bet.id,
                'market_id': bet.market.id,
                'market_question': bet.market.question,
                'outcome': bet.outcome,
                'amount': str(bet.amount),
                'entry_probability': bet.entry_probability,
                'result': bet.result,
                'payout': str(bet.payout) if bet.payout else None,
                'timestamp': bet.timestamp.isoformat()
            })
            
            # Calculate portfolio value for open positions (PENDING bets)
            if bet.result == 'PENDING':
                # Portfolio value = bet amount * current market probability
                current_probability = Decimal(bet.market.yes_probability) if bet.outcome == 'Yes' else Decimal(100 - bet.market.yes_probability)
                current_value = bet.amount * (current_probability / Decimal('100'))
                portfolio_value += current_value
        
        # Get user statistics
        stats = user.get_user_statistics()
        
        return JsonResponse({
            'user': {
                'id': user.id,
                'phone_number': user.phone_number,
                'full_name': user.full_name,
                'balance': str(user.balance),
                'kyc_verified': user.kyc_verified,
                'joined': user.date_joined.isoformat()
            },
            'statistics': stats,
            'bets': bets_data,
            'total_bets': len(bets_data),
            'portfolio': {
                'total_value': str(portfolio_value.quantize(Decimal('0.01')))
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def transaction_history(request):
    # Check authentication
    user = get_authenticated_user(request)
    if not user:
        logger.warning(f"History access denied - user not authenticated")
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        logger.info(f"Transaction history loaded for user: {user.phone_number}")
        transactions = Transaction.objects.filter(user=user)[:50]  # Last 50 transactions
        
        transactions_data = []
        for txn in transactions:
            transactions_data.append({
                'id': txn.id,
                'type': txn.type,
                'amount': str(txn.amount),
                'status': txn.status,
                'description': txn.description,
                'created_at': txn.created_at.isoformat()
            })
        
        return JsonResponse({
            'transactions': transactions_data,
            'total': len(transactions_data)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
@require_http_methods(["POST"])
def initiate_withdrawal(request):
    """Initiate M-Pesa withdrawal for user"""
    # Get authenticated user from session or header
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        amount = Decimal(str(data.get('amount')))
        
        if not amount or amount <= 0:
            return JsonResponse({'error': 'Invalid amount'}, status=400)
        
        # Check if user has enough balance
        if amount > user.balance:
            return JsonResponse({'error': f'Insufficient balance. Available: KSH {user.balance}'}, status=400)
        
        # Deduct from balance immediately (can be refunded if withdrawal fails)
        user.balance -= amount
        user.save()
        
        # Create transaction record
        transaction = Transaction.objects.create(
            user=user,
            type='WITHDRAWAL',
            amount=amount,
            phone_number=user.phone_number,
            status='PENDING',
            description=f'Withdrawal of KSH {amount}'
        )
        
        # TODO: Integrate with M-Pesa API to send money
        # For now, simulate successful withdrawal
        transaction.status = 'COMPLETED'
        transaction.save()
        
        return JsonResponse({
            'message': 'Withdrawal initiated successfully',
            'transaction_id': transaction.id,
            'amount': str(amount),
            'new_balance': str(user.balance)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
