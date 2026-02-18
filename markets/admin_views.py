import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from decimal import Decimal
from .models import Market, Bet
from payments.models import Transaction
from users.models import CustomUser
from api.validators import (
    validate_market_question,
    validate_market_category,
    validate_date_string,
    ValidationError
)

logger = logging.getLogger(__name__)

def is_admin(user, request=None):
    """Check if user is admin - checks both session auth and phone header"""
    # First try session-based auth
    if user and user.is_authenticated and user.is_staff:
        return True
    
    # Fallback to phone number header if session auth fails
    if request and request.headers.get('X-User-Phone-Number'):
        phone_number = request.headers.get('X-User-Phone-Number')
        try:
            user_obj = CustomUser.objects.get(phone_number=phone_number)
            return user_obj.is_staff and user_obj.is_superuser
        except CustomUser.DoesNotExist:
            return False
    
    return False


@require_http_methods(["GET"])
def admin_markets(request):
    """Get all markets for admin panel"""
    if not is_admin(request.user, request):
        return JsonResponse({'error': 'Admin access required'}, status=403)
    
    try:
        # Optional filters
        status_filter = request.GET.get('status', None)
        category_filter = request.GET.get('category', None)
        
        markets = Market.objects.all().order_by('-created_at')
        
        # Apply filters
        if status_filter and status_filter in ['OPEN', 'RESOLVED', 'CANCELLED']:
            markets = markets.filter(status=status_filter)
        
        if category_filter:
            markets = markets.filter(category=category_filter)
        
        markets_data = []
        for market in markets:
            total_bets = Bet.objects.filter(market=market).count()
            yes_bets = Bet.objects.filter(market=market, outcome='Yes').count()
            no_bets = Bet.objects.filter(market=market, outcome='No').count()
            
            total_wagered = Decimal('0')
            for bet in Bet.objects.filter(market=market):
                total_wagered += bet.amount
            
            markets_data.append({
                'id': market.id,
                'question': market.question,
                'category': market.category,
                'status': market.status,
                'resolved_outcome': market.resolved_outcome,
                'yes_probability': market.yes_probability,
                'yes_bets': yes_bets,
                'no_bets': no_bets,
                'total_bets': total_bets,
                'total_wagered': str(total_wagered),
                'end_date': market.end_date if isinstance(market.end_date, str) else market.end_date.isoformat(),
                'created_at': market.created_at.isoformat(),
                'resolved_at': market.resolved_at.isoformat() if market.resolved_at else None,
                'created_by': market.created_by.phone_number if market.created_by else None
            })
        
        return JsonResponse({
            'markets': markets_data,
            'total': len(markets_data)
        })
        
    except Exception as e:
        logger.error(f"Error fetching admin markets: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def resolve_market(request):
    """Resolve a market with a specific outcome"""
    if not is_admin(request.user, request):
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
        
        logger.info(f"Market {market_id} resolved with outcome '{outcome}': {payout_summary}")
        
        return JsonResponse({
            'message': 'Market resolved successfully',
            'market_id': market_id,
            'outcome': outcome,
            'payouts': payout_summary
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error resolving market: {str(e)}")
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
        
        payout_summary = {
            'total_wagered': str(total_wagered),
            'winners': winning_bets.count(),
            'losers': losing_bets.count(),
            'platform_fee': str(total_wagered * Decimal('0.1')),
            'payout_per_winner': '0',
            'transactions_created': 0,
            'users_updated': 0
        }
        
        # Mark losers
        for bet in losing_bets:
            bet.result = 'LOST'
            bet.payout = Decimal('0')
            bet.save()
            
            # Create payout transaction record
            try:
                Transaction.objects.create(
                    user=bet.user,
                    type='PAYOUT',
                    amount=Decimal('0'),
                    phone_number=bet.user.phone_number,
                    status='COMPLETED',
                    description=f'Bet lost on market: {market.question}',
                    related_bet=bet
                )
                payout_summary['transactions_created'] += 1
            except Exception as e:
                logger.error(f"Failed to create transaction for losing bet {bet.id}: {str(e)}")
        
        # Calculate and distribute winnings
        winning_amount = total_wagered * Decimal('0.9')  # 90% of total wagered (10% fee)
        
        if winning_bets.count() > 0:
            payout_per_bet = winning_amount / Decimal(str(winning_bets.count()))
            payout_summary['payout_per_winner'] = str(payout_per_bet)
            
            for bet in winning_bets:
                payout = bet.amount + payout_per_bet
                bet.result = 'WON'
                bet.payout = payout
                bet.save()
                
                # Update user balance
                user = bet.user
                user.balance += payout
                user.save()
                payout_summary['users_updated'] += 1
                
                # Create payout transaction record
                try:
                    Transaction.objects.create(
                        user=user,
                        type='PAYOUT',
                        amount=payout,
                        phone_number=user.phone_number,
                        status='COMPLETED',
                        description=f'Winnings from market: {market.question}',
                        related_bet=bet
                    )
                    payout_summary['transactions_created'] += 1
                except Exception as e:
                    logger.error(f"Failed to create transaction for winning bet {bet.id}: {str(e)}")
        
        return payout_summary
        
    except Exception as e:
        logger.error(f"Error processing market payouts for market {market.id}: {str(e)}")
        raise e


@csrf_exempt
@require_http_methods(["POST"])
def create_market(request):
    """Create a new market (admin only)"""
    if not is_admin(request.user, request):
        return JsonResponse({'error': 'Admin access required'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['question', 'category', 'end_date']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return JsonResponse({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)
        
        # Validate inputs
        try:
            question = validate_market_question(data.get('question'))
            category = validate_market_category(data.get('category'))
            end_date = validate_date_string(data.get('end_date'))
        except ValidationError as e:
            return JsonResponse({'error': e.message}, status=400)
        
        # Get user from header for created_by field
        phone_number = request.headers.get('X-User-Phone-Number')
        created_by = None
        if phone_number:
            try:
                created_by = CustomUser.objects.get(phone_number=phone_number)
            except CustomUser.DoesNotExist:
                pass
        
        # Create market
        market = Market.objects.create(
            question=question,
            category=category,
            description=data.get('description', ''),
            image_url=data.get('image_url', ''),
            end_date=end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date),
            created_by=created_by
        )
        
        logger.info(f"Market {market.id} created by {request.user.id}: {question}")
        
        return JsonResponse({
            'message': 'Market created successfully',
            'market': {
                'id': market.id,
                'question': market.question,
                'category': market.category,
                'status': market.status,
                'end_date': market.end_date if isinstance(market.end_date, str) else market.end_date.isoformat(),
                'created_at': market.created_at.isoformat()
            }
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ValidationError as e:
        return JsonResponse({'error': e.message}, status=400)
    except Exception as e:
        logger.error(f"Error creating market: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
