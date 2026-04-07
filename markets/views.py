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
    """
    Get authenticated user from either:
    1. Session (if session cookie exists)
    2. X-User-Phone-Number header (for phone auth)
    3. X-User-Email header (for Google OAuth users)
    """
    # Try session-based auth first
    if request.user and request.user.is_authenticated:
        return request.user
    
    # Fall back to phone number header (phone auth)
    phone_number = request.headers.get('X-User-Phone-Number')
    if phone_number:
        try:
            user = CustomUser.objects.get(phone_number=phone_number)
            if user.is_active:
                return user
        except CustomUser.DoesNotExist:
            pass
    
    # Fall back to email header (Google OAuth)
    email = request.headers.get('X-User-Email')
    if email:
        try:
            user = CustomUser.objects.get(email=email)
            if user.is_active:
                return user
        except CustomUser.DoesNotExist:
            pass
    
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
        
        # Handle OPTION_LIST markets
        option_id = None
        option_label = None
        entry_probability = market.yes_probability
        
        if market.market_type == 'OPTION_LIST':
            option_id = data.get('option_id')
            if not option_id:
                return JsonResponse({'error': 'option_id is required for option list markets'}, status=400)
            
            # Find the option and get its probability
            if market.options and isinstance(market.options, list):
                matching_option = next((opt for opt in market.options if opt.get('id') == option_id), None)
                if not matching_option:
                    return JsonResponse({'error': f'Option {option_id} not found'}, status=400)
                
                option_label = matching_option.get('label')
                if outcome == 'Yes':
                    entry_probability = matching_option.get('yes_probability', 50)
                else:
                    entry_probability = matching_option.get('no_probability', 50)
        
        # Get action type (buy or sell)
        action = data.get('action', 'buy').lower()
        if action not in ['buy', 'sell']:
            return JsonResponse({'error': 'Invalid action. Must be buy or sell'}, status=400)
        
        # Handle buy (deduct from balance) vs sell (add to balance)
        if action == 'buy':
            # Check if user has sufficient balance
            if amount > user.balance:
                return JsonResponse({'error': f'Insufficient balance. Available: KSH {user.balance}'}, status=400)
            # Deduct from balance
            user.balance -= amount
        else:  # sell
            # Add to balance (proceeds from selling)
            user.balance += amount
        
        user.save()
        
        order_type = data.get('order_type', 'MARKET')
        if order_type not in ['MARKET', 'LIMIT']:
            order_type = 'MARKET'

        try:
            quantity = int(data.get('quantity', 1))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Quantity must be an integer'}, status=400)

        if quantity < 1:
            return JsonResponse({'error': 'Quantity must be at least 1'}, status=400)

        limit_price = None
        if order_type == 'LIMIT':
            limit_price_raw = data.get('limit_price')
            if limit_price_raw in [None, '']:
                return JsonResponse({'error': 'Limit price is required for limit orders'}, status=400)
            try:
                limit_price = validate_amount(limit_price_raw, min_amount=Decimal('0.01'), max_amount=Decimal('1000000'))
            except ValidationError as e:
                return JsonResponse({'error': e.message}, status=400)

        # Create the bet
        bet = Bet.objects.create(
            user=user,
            market=market,
            outcome=outcome,
            amount=amount,
            entry_probability=entry_probability,
            option_id=option_id,
            option_label=option_label,
            order_type=order_type,
            limit_price=limit_price,
            quantity=quantity,
            action=action.upper(),
        )
        
        # Create transaction record
        transaction_type = 'BET_SELL' if action == 'sell' else 'BET'
        if market.market_type == 'OPTION_LIST' and option_label:
            description = f'Position closed on: {option_label}' if action == 'sell' else f'Bet placed on: {option_label}'
        else:
            description = f'Position closed on: {market.question}' if action == 'sell' else f'Bet placed on: {market.question}'
        
        Transaction.objects.create(
            user=user,
            type=transaction_type,
            amount=amount,
            phone_number=user.phone_number,
            status='COMPLETED',
            description=description,
            related_bet=bet
        )
        
        # Create notification
        action_text = 'sold' if action == 'sell' else 'placed'
        notification_type = 'BET_SOLD' if action == 'sell' else 'BET_PLACED'
        notification_title = 'Position Closed' if action == 'sell' else 'Bet Placed'
        create_notification(
            user=user,
            type_choice=notification_type,
            title=notification_title,
            message=f'Your prediction of {outcome} for KSh {amount} has been {action_text}',
            color_class='green' if action == 'sell' else 'purple',
            related_market_id=market.id,
            related_bet_id=bet.id
        )
        
        # Update probability for BINARY markets only
        if market.market_type == 'BINARY':
            if outcome == 'Yes':
                market.yes_probability = min(99, market.yes_probability + 1)
            else:
                market.yes_probability = max(1, market.yes_probability - 1)
        # For OPTION_LIST markets, update the specific option probability
        elif market.market_type == 'OPTION_LIST' and market.options:
            for opt in market.options:
                if opt.get('id') == option_id:
                    if outcome == 'Yes':
                        opt['yes_probability'] = min(99, opt.get('yes_probability', 50) + 1)
                    else:
                        opt['no_probability'] = min(99, opt.get('no_probability', 50) + 1)
                        opt['yes_probability'] = 100 - opt['no_probability']
                    break
            market.options = market.options  # Trigger update

        current_volume = parse_volume_value(market.volume)
        market.volume = format_volume_value(current_volume + int(amount))
        market.save()
        
        # Record price history after market is updated
        from markets.models import PriceHistory
        if market.market_type == 'BINARY':
            PriceHistory.objects.create(
                market=market,
                yes_probability=market.yes_probability,
                no_probability=100 - market.yes_probability
            )
        elif market.market_type == 'OPTION_LIST' and market.options:
            for opt in market.options:
                PriceHistory.objects.create(
                    market=market,
                    option_id=opt.get('id'),
                    yes_probability=opt.get('yes_probability', 50),
                    no_probability=opt.get('no_probability', 50)
                )
        
        action_verb = 'sold' if action == 'sell' else 'placed'
        logger.info(f"Bet {action_verb} by {user.phone_number}: {outcome} {amount} on market {market_id}")

        response_msg = 'Position closed successfully' if action == 'sell' else 'Bet placed successfully'
        return JsonResponse({
            'message': response_msg, 
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


@require_http_methods(["GET"])
def market_details(request, market_id):
    """Return market public details for comments, top holders, positions, and activity."""
    try:
        try:
            market = Market.objects.get(id=market_id)
        except Market.DoesNotExist:
            return JsonResponse({'error': 'Market not found'}, status=404)

        comments = ChatMessage.objects.filter(market=market).select_related('user', 'parent__user').order_by('created_at')
        bets = Bet.objects.filter(market=market).select_related('user').order_by('-timestamp')

        # Build comment list
        comment_data = [
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
            for msg in comments
        ]

        # Public positions list
        positions = [
            {
                'id': bet.id,
                'user_id': bet.user.id,
                'user_name': bet.user.full_name,
                'outcome': bet.outcome,
                'order_type': bet.order_type,
                'limit_price': str(bet.limit_price) if bet.limit_price is not None else None,
                'quantity': bet.quantity,
                'amount': str(bet.amount),
                'entry_probability': bet.entry_probability,
                'result': bet.result,
                'timestamp': bet.timestamp.isoformat(),
            }
            for bet in bets
        ]

        # Group top holders by user and outcome
        holder_map = {}
        for bet in bets:
            key = (bet.user.id, bet.outcome)
            if key not in holder_map:
                holder_map[key] = {
                    'user_id': bet.user.id,
                    'user_name': bet.user.full_name,
                    'outcome': bet.outcome,
                    'shares': 0,
                    'average_price': Decimal('0.00'),
                    'amount_total': Decimal('0.00'),
                }
            holder_map[key]['shares'] += bet.quantity or 1
            holder_map[key]['amount_total'] += bet.amount

        for holder in holder_map.values():
            shares = Decimal(holder['shares']) if holder['shares'] else Decimal('1')
            holder['average_price'] = str((holder['amount_total'] / shares).quantize(Decimal('0.01')))
            holder['shares'] = int(holder['shares'])
            holder.pop('amount_total', None)

        yes_holders = sorted(
            [holder for holder in holder_map.values() if holder['outcome'] == 'Yes'],
            key=lambda h: h['shares'],
            reverse=True
        )
        no_holders = sorted(
            [holder for holder in holder_map.values() if holder['outcome'] == 'No'],
            key=lambda h: h['shares'],
            reverse=True
        )

        # Build activity stream
        activity = [
            {
                'id': bet.id,
                'user_id': bet.user.id,
                'user_name': bet.user.full_name,
                'action': f"bought {bet.quantity or 1} {bet.outcome}",
                'amount': str(bet.amount),
                'limit_price': str(bet.limit_price) if bet.limit_price is not None else None,
                'order_type': bet.order_type,
                'timestamp': bet.timestamp.isoformat(),
            }
            for bet in bets
        ]

        return JsonResponse({
            'market_id': market.id,
            'comments': comment_data,
            'positions': positions,
            'top_holders': {
                'yes': yes_holders,
                'no': no_holders,
            },
            'activity': activity,
        })
    except Exception as e:
        logger.error(f"Market details error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(['GET'])
def get_price_history(request, market_id):
    """Get historical price data for a market based on time period"""
    try:
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        market = Market.objects.get(id=market_id)
        period = request.GET.get('period', 'ALL')
        option_id = request.GET.get('option_id')
        
        # Calculate time range based on period
        now = timezone.now()
        time_ranges = {
            '1H': now - timedelta(hours=1),
            '6H': now - timedelta(hours=6),
            '1D': now - timedelta(days=1),
            '1W': now - timedelta(weeks=1),
            '1M': now - timedelta(days=30),
            'ALL': now - timedelta(days=365),
        }
        
        start_time = time_ranges.get(period, now - timedelta(days=365))
        
        # Fetch price history
        from markets.models import PriceHistory
        query = PriceHistory.objects.filter(
            market=market,
            timestamp__gte=start_time
        )
        if option_id:
            query = query.filter(option_id=option_id)
        else:
            query = query.filter(option_id__isnull=True)  # For BINARY markets
        
        history = query.order_by('timestamp')
        
        # If no history, return empty array
        if not history.exists():
            return JsonResponse({
                'market_id': market.id,
                'period': period,
                'option_id': option_id,
                'data': []
            })
        
        # Format data for frontend
        data = [
            {
                'timestamp': h.timestamp.isoformat(),
                'yes_probability': h.yes_probability,
                'no_probability': h.no_probability,
            }
            for h in history
        ]
        
        return JsonResponse({
            'market_id': market.id,
            'period': period,
            'option_id': option_id,
            'data': data
        })
    except Market.DoesNotExist:
        return JsonResponse({'error': 'Market not found'}, status=404)
    except Exception as e:
        logger.error(f"Price history error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

