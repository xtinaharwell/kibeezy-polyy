import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .models import Market, Bet
from payments.models import Transaction

logger = logging.getLogger(__name__)

def list_markets(request):
    markets = Market.objects.all().values()
    return JsonResponse(list(markets), safe=False)

@csrf_exempt
@require_http_methods(["POST"])
def place_bet(request):
    # Check authentication first
    if not request.user or not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        market_id = data.get('market_id')
        outcome = data.get('outcome')
        amount = Decimal(str(data.get('amount')))

        if not all([market_id, outcome, amount]):
            return JsonResponse({'error': 'Missing bet details'}, status=400)
        
        if outcome not in ['Yes', 'No']:
            return JsonResponse({'error': 'Outcome must be Yes or No'}, status=400)

        try:
            market = Market.objects.get(id=market_id)
        except Market.DoesNotExist:
            return JsonResponse({'error': 'Market not found'}, status=404)
        
        # Check if market is open
        if market.status != 'OPEN':
            return JsonResponse({'error': f'Market is {market.status.lower()}'}, status=400)
        
        user = request.user
        
        # Check if user has sufficient balance
        if amount > user.balance:
            return JsonResponse({'error': f'Insufficient balance. Available: KSH {user.balance}'}, status=400)
        
        # Deduct from balance
        user.balance -= amount
        user.save()
        
        # Create the bet
        bet = Bet.objects.create(
            user=user,
            market=market,
            outcome=outcome,
            amount=amount,
            entry_probability=market.yes_probability
        )
        
        # Create transaction record
        Transaction.objects.create(
            user=user,
            type='BET',
            amount=amount,
            phone_number=user.phone_number,
            status='COMPLETED',
            description=f'Bet placed on: {market.question}',
            related_bet=bet
        )
        
        # Simple logic to update probability (for demonstration)
        if outcome == 'Yes':
            market.yes_probability = min(99, market.yes_probability + 1)
        else:
            market.yes_probability = max(1, market.yes_probability - 1)
        market.save()
        
        logger.info(f"Bet placed by {user.phone_number}: {outcome} {amount} on market {market_id}")

        return JsonResponse({
            'message': 'Bet placed successfully', 
            'bet_id': bet.id,
            'new_balance': str(user.balance)
        })
    except Market.DoesNotExist:
        return JsonResponse({'error': 'Market not found'}, status=404)
    except Exception as e:
        logger.error(f"Place bet error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
