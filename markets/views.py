import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Market, Bet

def list_markets(request):
    markets = Market.objects.all().values()
    return JsonResponse(list(markets), safe=False)

@csrf_exempt
def place_bet(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        try:
            data = json.loads(request.body)
            market_id = data.get('market_id')
            outcome = data.get('outcome')
            amount = data.get('amount')

            if not all([market_id, outcome, amount]):
                return JsonResponse({'error': 'Missing bet details'}, status=400)

            market = Market.objects.get(id=market_id)
            bet = Bet.objects.create(
                user=request.user,
                market=market,
                outcome=outcome,
                amount=amount
            )
            
            # Simple logic to update probability (for demonstration)
            if outcome == 'Yes':
                market.yes_probability = min(99, market.yes_probability + 1)
            else:
                market.yes_probability = max(1, market.yes_probability - 1)
            market.save()

            return JsonResponse({'message': 'Bet placed successfully', 'bet_id': bet.id})
        except Market.DoesNotExist:
            return JsonResponse({'error': 'Market not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)
