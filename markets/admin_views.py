import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import datetime
from decimal import Decimal
from .models import Market, Bet
from payments.models import Transaction
from users.models import CustomUser

def is_admin(user):
    """Check if user is admin"""
    return user and user.is_authenticated and user.is_staff


@csrf_exempt
@require_http_methods(["GET"])
def admin_markets(request):
    """Get all markets for admin panel"""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Admin access required'}, status=403)
    
    try:
        markets = Market.objects.all().order_by('-created_at')
        
        markets_data = []
        for market in markets:
            total_bets = Bet.objects.filter(market=market).count()
            yes_bets = Bet.objects.filter(market=market, outcome='Yes').count()
            no_bets = Bet.objects.filter(market=market, outcome='No').count()
            
            markets_data.append({
                'id': market.id,
                'question': market.question,
                'category': market.category,
                'status': market.status,
                'resolved_outcome': market.resolved_outcome,
                'yes_probability': market.yes_probability,
                'total_bets': total_bets,
                'yes_bets': yes_bets,
                'no_bets': no_bets,
                'end_date': market.end_date,
                'created_at': market.created_at.isoformat()
            })
        
        return JsonResponse({
            'markets': markets_data,
            'total': len(markets_data)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def resolve_market(request):
    """Resolve a market with a specific outcome"""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Admin access required'}, status=403)
    
    try:
        data = json.loads(request.body)
        market_id = data.get('market_id')
        outcome = data.get('outcome')  # 'Yes' or 'No'
        
        if not market_id or outcome not in ['Yes', 'No']:
            return JsonResponse({'error': 'Invalid market_id or outcome'}, status=400)
        
        try:
            market = Market.objects.get(id=market_id)
        except Market.DoesNotExist:
            return JsonResponse({'error': 'Market not found'}, status=404)
        
        if market.status == 'RESOLVED':
            return JsonResponse({'error': 'Market already resolved'}, status=400)
        
        # Update market status
        market.status = 'RESOLVED'
        market.resolved_outcome = outcome
        market.resolved_at = datetime.now()
        market.is_live = False
        market.save()
        
        # Calculate and distribute payouts
        payout_summary = process_market_payouts(market, outcome)
        
        return JsonResponse({
            'message': 'Market resolved successfully',
            'market_id': market_id,
            'outcome': outcome,
            'payouts': payout_summary
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def process_market_payouts(market, outcome):
    """Process payouts for all bets in a market"""
    try:
        winning_bets = Bet.objects.filter(market=market, outcome=outcome)
        losing_bets = Bet.objects.filter(market=market).exclude(outcome=outcome)
        
        # Calculate total wagered
        total_wagered = Decimal('0')
        for bet in Bet.objects.filter(market=market):
            total_wagered += bet.amount
        
        # Mark losers
        for bet in losing_bets:
            bet.result = 'LOST'
            bet.payout = Decimal('0')
            bet.save()
            
            # Create payout transaction record
            Transaction.objects.create(
                user=bet.user,
                type='PAYOUT',
                amount=Decimal('0'),
                phone_number=bet.user.phone_number,
                status='COMPLETED',
                description=f'Bet lost on market: {market.question}',
                related_bet=bet
            )
        
        # Calculate and distribute winnings
        winning_amount = total_wagered * Decimal('0.9')  # 90% of total wagered (10% fee)
        
        if winning_bets.count() > 0:
            payout_per_bet = winning_amount / Decimal(str(winning_bets.count()))
            
            for bet in winning_bets:
                payout = bet.amount + payout_per_bet
                bet.result = 'WON'
                bet.payout = payout
                bet.save()
                
                # Update user balance
                user = bet.user
                user.balance += payout
                user.save()
                
                # Create payout transaction record
                Transaction.objects.create(
                    user=user,
                    type='PAYOUT',
                    amount=payout,
                    phone_number=user.phone_number,
                    status='COMPLETED',
                    description=f'Winnings from market: {market.question}',
                    related_bet=bet
                )
        
        return {
            'total_wagered': str(total_wagered),
            'winners': winning_bets.count(),
            'losers': losing_bets.count(),
            'payout_per_winner': str(winning_amount / Decimal(str(winning_bets.count()))) if winning_bets.count() > 0 else '0'
        }
    except Exception as e:
        raise e


@csrf_exempt
@require_http_methods(["POST"])
def create_market(request):
    """Create a new market (admin only)"""
    if not is_admin(request.user):
        return JsonResponse({'error': 'Admin access required'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        required_fields = ['question', 'category', 'end_date']
        if not all(field in data for field in required_fields):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        market = Market.objects.create(
            question=data.get('question'),
            category=data.get('category'),
            description=data.get('description', ''),
            image_url=data.get('image_url', ''),
            end_date=data.get('end_date'),
            created_by=request.user
        )
        
        return JsonResponse({
            'message': 'Market created successfully',
            'market': {
                'id': market.id,
                'question': market.question,
                'category': market.category,
                'status': market.status
            }
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
