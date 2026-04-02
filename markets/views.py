import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from .models import Market, Bet, ChatMessage
from payments.models import Transaction
from api.validators import validate_amount, validate_bet_outcome, ValidationError
from users.models import CustomUser
from notifications.views import create_notification


def parse_volume_value(volume_str: str) -> int:
    """Convert a formatted volume string to an integer amount in KES."""
    if not volume_str:
        return 0
    normalized = volume_str.replace('KSh', '').replace('KES', '').replace(' ', '').strip()
    if normalized.endswith(('M', 'm')):
        try:
            return int(float(normalized[:-1]) * 1_000_000)
        except ValueError:
            return 0
    if normalized.endswith(('K', 'k')):
        try:
            return int(float(normalized[:-1]) * 1_000)
        except ValueError:
            return 0
    try:
        return int(float(normalized))
    except ValueError:
        return 0


def format_volume_value(amount: int) -> str:
    """Format a KES amount into a human-readable volume string."""
    if amount >= 1_000_000:
        return f"KSh {amount / 1_000_000:.1f}M".replace('.0M', 'M')
    if amount >= 1_000:
        return f"KSh {amount / 1_000:.1f}K".replace('.0K', 'K')
    return f"KSh {amount}"

logger = logging.getLogger(__name__)

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


def list_markets(request):
    markets = Market.objects.all().values()
    return JsonResponse(list(markets), safe=False)

@csrf_exempt
@require_http_methods(["POST"])
def place_bet(request):
    # Get authenticated user from session or header
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    try:
        data = json.loads(request.body)
        market_id = data.get('market_id')
        outcome = data.get('outcome')
        amount = data.get('amount')

        if not all([market_id, outcome, amount]):
            return JsonResponse({'error': 'Missing bet details: market_id, outcome, amount'}, status=400)
        
        # Validate outcome
        try:
            outcome = validate_bet_outcome(outcome)
        except ValidationError as e:
            return JsonResponse({'error': e.message}, status=400)
        
        # Validate amount
        try:
            amount = validate_amount(amount, min_amount=Decimal('1'), max_amount=Decimal('100000'))
        except ValidationError as e:
            return JsonResponse({'error': e.message}, status=400)

        try:
            market = Market.objects.get(id=market_id)
        except Market.DoesNotExist:
            return JsonResponse({'error': 'Market not found'}, status=404)
        
        # Check if market is open
        if market.status != 'OPEN':
            return JsonResponse({'error': f'Market is {market.status.lower()}'}, status=400)
        
        # Check if user has sufficient balance
        if amount > user.balance:
            return JsonResponse({'error': f'Insufficient balance. Available: KSH {user.balance}'}, status=400)
        
        # Deduct from balance
        user.balance -= amount
        user.save()
        
        order_type = data.get('order_type', 'MARKET')
        if order_type not in ['MARKET', 'LIMIT']:
            order_type = 'MARKET'

        # Create the bet
        bet = Bet.objects.create(
            user=user,
            market=market,
            outcome=outcome,
            amount=amount,
            entry_probability=market.yes_probability,
            order_type=order_type
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
        
        # Create bet placed notification
        create_notification(
            user=user,
            type_choice='BET_PLACED',
            title='Bet Placed',
            message=f'Your prediction of {outcome} for KSh {amount} has been placed',
            color_class='purple',
            related_market_id=market.id,
            related_bet_id=bet.id
        )
        
        # Simple logic to update probability (for demonstration)
        if outcome == 'Yes':
            market.yes_probability = min(99, market.yes_probability + 1)
        else:
            market.yes_probability = max(1, market.yes_probability - 1)

        current_volume = parse_volume_value(market.volume)
        market.volume = format_volume_value(current_volume + int(amount))
        market.save()
        
        logger.info(f"Bet placed by {user.phone_number}: {outcome} {amount} on market {market_id}")

        return JsonResponse({
            'message': 'Bet placed successfully', 
            'bet_id': bet.id,
            'new_balance': str(user.balance)
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Market.DoesNotExist:
        return JsonResponse({'error': 'Market not found'}, status=404)
    except ValidationError as e:
        return JsonResponse({'error': e.message}, status=400)
    except Exception as e:
        logger.error(f"Place bet error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def market_chat(request, market_id):
    """Chat messages for a single market."""
    try:
        try:
            market = Market.objects.get(id=market_id)
        except Market.DoesNotExist:
            return JsonResponse({'error': 'Market not found'}, status=404)

        if request.method == 'GET':
            messages = ChatMessage.objects.filter(market=market).select_related('user', 'parent__user').order_by('created_at')
            return JsonResponse({
                'messages': [
                    {
                        'id': msg.id,
                        'user_id': msg.user.id,
                        'user_name': msg.user.full_name,
                        'phone_number': msg.user.phone_number,
                        'message': msg.message,
                        'created_at': msg.created_at.isoformat(),
                        'parent_id': msg.parent_id,
                        'parent_user_name': msg.parent.user.full_name if msg.parent else None,
                    }
                    for msg in messages
                ]
            })

        # POST
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        data = json.loads(request.body)
        message = data.get('message', '').strip()
        reply_to = data.get('reply_to')

        if not message:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)

        parent_message = None
        if reply_to:
            try:
                parent_message = ChatMessage.objects.get(id=reply_to, market=market)
            except ChatMessage.DoesNotExist:
                return JsonResponse({'error': 'Reply target not found'}, status=400)

        chat_message = ChatMessage.objects.create(
            user=user,
            market=market,
            parent=parent_message,
            message=message,
        )

        return JsonResponse({
            'message': {
                'id': chat_message.id,
                'user_id': user.id,
                'user_name': user.full_name,
                'phone_number': user.phone_number,
                'message': chat_message.message,
                'created_at': chat_message.created_at.isoformat(),
                'parent_id': chat_message.parent_id,
                'parent_user_name': chat_message.parent.user.full_name if chat_message.parent else None,
            }
        }, status=201)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Market chat error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
