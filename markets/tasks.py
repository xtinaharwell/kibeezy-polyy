"""
Celery tasks for limit order matching and execution
"""
import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction as db_transaction
from markets.models import Market, Bet
from payments.models import Transaction
from notifications.views import create_notification

logger = logging.getLogger(__name__)

# Try to import celery - will be available in production
try:
    from celery import shared_task
except ImportError:
    # Development mode without Celery
    def shared_task(*args, **kwargs):
        """Dummy decorator when Celery is not installed"""
        def decorator(func):
            return func
        if args and callable(args[0]):
            return args[0]
        return decorator


def match_limit_orders_impl():
    """
    Core logic for matching and executing pending limit orders.
    Called by Celery task or manually for testing.
    """
    try:
        # Get all PENDING limit orders for OPEN markets
        pending_orders = Bet.objects.filter(
            order_type='LIMIT',
            order_status='PENDING',
            market__status='OPEN'
        ).select_related('user', 'market')
        
        executed_count = 0
        
        for bet in pending_orders:
            try:
                if _should_execute_limit_order(bet):
                    _execute_limit_order(bet)
                    executed_count += 1
            except Exception as e:
                logger.error(f"Error executing limit order {bet.id}: {str(e)}")
                continue
        
        logger.info(f"Matched and executed {executed_count} limit orders")
        return {'status': 'success', 'executed_orders': executed_count}
        
    except Exception as e:
        logger.error(f"Error in match_limit_orders: {str(e)}")
        raise


# Apply Celery decorator if available
try:
    @shared_task(bind=True, max_retries=3, default_retry_delay=60)
    def match_limit_orders(self):
        """Celery wrapper for match_limit_orders_impl"""
        try:
            result = match_limit_orders_impl()
            return result
        except Exception as e:
            logger.error(f"Error in match_limit_orders task: {str(e)}")
            raise self.retry(exc=e, countdown=60)
except:
    # If Celery is not available, just use the impl function
    def match_limit_orders():
        return match_limit_orders_impl()


def expire_unmatched_limit_orders_impl():
    """
    Core logic for marking limit orders as expired.
    Called by Celery task or manually for testing.
    """
    try:
        # Get all PENDING limit orders for CLOSED/RESOLVED markets
        expired_orders = Bet.objects.filter(
            order_type='LIMIT',
            order_status='PENDING'
        ).exclude(
            market__status='OPEN'
        )
        
        expired_count = 0
        
        for bet in expired_orders:
            bet.order_status = 'EXPIRED'
            bet.save()
            
            # Create notification
            create_notification(
                user=bet.user,
                type_choice='LIMIT_ORDER_EXPIRED',
                title='Limit Order Expired',
                message=f'Your limit {bet.action.lower()} order for {bet.outcome} on "{bet.market.question}" expired without filling.',
                color_class='orange',
                related_market_id=bet.market.id,
                related_bet_id=bet.id
            )
            
            expired_count += 1
        
        logger.info(f"Expired {expired_count} unmatched limit orders")
        return {'status': 'success', 'expired_orders': expired_count}
        
    except Exception as e:
        logger.error(f"Error in expire_unmatched_limit_orders: {str(e)}")
        raise


# Apply Celery decorator if available
try:
    @shared_task
    def expire_unmatched_limit_orders():
        """Celery wrapper for expire_unmatched_limit_orders_impl"""
        return expire_unmatched_limit_orders_impl()
except:
    # If Celery is not available, just use the impl function
    def expire_unmatched_limit_orders():
        return expire_unmatched_limit_orders_impl()


def _should_execute_limit_order(bet: Bet) -> bool:
    """
    Check if a limit order should be executed based on current market price.
    
    BUY order: Execute when market price <= limit_price
    SELL order: Execute when market price >= limit_price
    """
    if bet.action != 'BUY' and bet.action != 'SELL':
        return False
    
    # Get current market price for the outcome
    current_price = Decimal(str(bet.market.yes_probability)) if bet.outcome == 'Yes' else Decimal('100') - Decimal(str(bet.market.yes_probability))
    limit_price = bet.limit_price
    
    if bet.action == 'BUY':
        # Buy order executes if price drops to or below limit price
        return current_price <= limit_price
    else:  # SELL
        # Sell order executes if price rises to or above limit price
        return current_price >= limit_price


def _execute_limit_order(bet: Bet):
    """
    Execute a matched limit order:
    - Deduct/add balance
    - Create transaction
    - Update order status
    - Send notification
    """
    with db_transaction.atomic():
        user = bet.user
        
        # Update balance based on action
        if bet.action == 'BUY':
            # Check if user still has sufficient balance
            if bet.amount > user.balance:
                logger.warning(f"User {user.id} no longer has sufficient balance for limit order {bet.id}")
                return
            user.balance -= bet.amount
        else:  # SELL
            # Check if user still owns the shares (may have sold them in the meantime)
            from django.db.models import Sum
            
            buy_quantity = Bet.objects.filter(
                user=user,
                market=bet.market,
                outcome=bet.outcome,
                action='BUY',
                option_id=bet.option_id
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            sell_quantity = Bet.objects.filter(
                user=user,
                market=bet.market,
                outcome=bet.outcome,
                action='SELL',
                option_id=bet.option_id,
                order_status='FILLED'  # Only count filled sell orders
            ).exclude(id=bet.id).aggregate(total=Sum('quantity'))['total'] or 0
            
            available_quantity = buy_quantity - sell_quantity
            
            if bet.amount > Decimal(str(available_quantity)):
                logger.warning(f"User {user.id} no longer owns shares for limit order {bet.id}")
                return
            
            user.balance += bet.amount
        
        user.save()
        
        # Update bet order status
        now = timezone.now()
        bet.order_status = 'FILLED'
        bet.filled_at = now
        bet.save()
        
        # Create transaction record
        transaction_type = 'BET_SELL' if bet.action == 'SELL' else 'BET'
        if bet.market.market_type == 'OPTION_LIST' and bet.option_label:
            description = f'Limit {bet.action.lower()} order filled on: {bet.option_label} @ {bet.limit_price}%'
        else:
            description = f'Limit {bet.action.lower()} order filled on: {bet.market.question} @ {bet.limit_price}%'
        
        Transaction.objects.create(
            user=user,
            type=transaction_type,
            amount=bet.amount,
            phone_number=user.phone_number,
            status='COMPLETED',
            description=description,
            related_bet=bet
        )
        
        # Create notification
        action_text = 'sold' if bet.action == 'SELL' else 'bought'
        create_notification(
            user=user,
            type_choice='LIMIT_ORDER_FILLED',
            title='Limit Order Filled',
            message=f'Your limit {bet.action.lower()} order for {bet.outcome} has been filled at {bet.limit_price}%',
            color_class='green',
            related_market_id=bet.market.id,
            related_bet_id=bet.id
        )
        
        logger.info(f"Executed limit order {bet.id} for user {user.phone_number}")
