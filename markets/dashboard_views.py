import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .models import Market, Bet
from payments.models import Transaction

@csrf_exempt
@require_http_methods(["GET"])
def user_dashboard(request):
    """Get user dashboard data: balance, bet history, statistics"""
    if not request.user or not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        user = request.user
        
        # Get user bets with market info
        bets = Bet.objects.filter(user=user).select_related('market').order_by('-timestamp')
        
        bets_data = []
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
            'total_bets': len(bets_data)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def transaction_history(request):
    """Get user's transaction history"""
    if not request.user or not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        user = request.user
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


@csrf_exempt
@require_http_methods(["POST"])
def initiate_withdrawal(request):
    """Initiate M-Pesa withdrawal for user"""
    if not request.user or not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        amount = Decimal(str(data.get('amount')))
        
        if not amount or amount <= 0:
            return JsonResponse({'error': 'Invalid amount'}, status=400)
        
        user = request.user
        
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
