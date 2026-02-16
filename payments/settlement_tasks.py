"""
Celery tasks for market settlement and payout processing
Calculates pari-mutuel payouts and initiates B2C transfers
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from celery import shared_task
from markets.models import Market, Bet
from payments.models import Transaction
from users.models import CustomUser
from payments.daraja_b2c import call_b2c, normalize_phone

logger = logging.getLogger(__name__)

# Platform fees - customize as needed
PLATFORM_FEE_PCT = Decimal('5.00')  # 5% platform fee
MIN_PAYOUT = Decimal('10')  # Don't send payouts < KES 10


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def settle_market(self, market_id):
    """
    Settlement task for a resolved market
    
    Flow:
    1. Validate market is CLOSED and has resolved_outcome
    2. Calculate total pool and winner pool
    3. Calculate payout for each winning bet
    4. Create payout transactions
    5. Enqueue B2C calls
    6. Mark market as RESOLVED
    
    Args:
        market_id: Market.id to settle
    
    Returns:
        dict with settlement summary
    """
    try:
        with transaction.atomic():
            # Lock market to prevent concurrent settlement
            market = Market.objects.select_for_update().get(pk=market_id)
            
            # Validate market state
            if market.status == 'RESOLVED':
                logger.warning(f"Market {market_id} already resolved, skipping settlement")
                return {'status': 'already_resolved'}
            
            if market.status != 'CLOSED':
                logger.warning(f"Market {market_id} not closed, current status: {market.status}")
                return {'status': 'not_closed', 'current_status': market.status}
            
            if not market.resolved_outcome:
                logger.error(f"Market {market_id} closed but no resolved_outcome set")
                return {'status': 'error', 'error': 'no_resolved_outcome'}
            
            # Calculate total pool and winners pool
            all_bets = Bet.objects.filter(market=market)
            total_pool = sum(Decimal(str(bet.amount)) for bet in all_bets)
            
            if total_pool == 0:
                logger.warning(f"Market {market_id} has zero pool, no settlement")
                market.status = 'RESOLVED'
                market.save()
                return {'status': 'no_bets', 'total_pool': 0}
            
            # Get winning bets
            winning_bets = all_bets.filter(outcome=market.resolved_outcome)
            winners_pool = sum(Decimal(str(bet.amount)) for bet in winning_bets)
            
            if winners_pool == 0:
                logger.warning(f"Market {market_id} resolved but no winning bets, refunding all")
                # Refund all bettors
                for bet in all_bets:
                    _create_refund_transaction(bet)
                market.status = 'RESOLVED'
                market.save()
                return {'status': 'no_winners', 'refunded_count': all_bets.count()}
            
            # Calculate distributable pool (after platform fee)
            platform_fee_amount = (PLATFORM_FEE_PCT / Decimal('100')) * total_pool
            distributable_pool = total_pool - platform_fee_amount
            
            logger.info(
                f"Settling market {market_id}: "
                f"total_pool={total_pool}, winners_pool={winners_pool}, "
                f"distributable={distributable_pool}, fee={platform_fee_amount}"
            )
            
            # Create payout transactions for each winner
            payout_count = 0
            payout_amount_total = Decimal('0')
            
            for bet in winning_bets:
                # Pari-mutuel payout formula
                payout_gross = (Decimal(str(bet.amount)) / winners_pool) * distributable_pool
                payout_amount = round(payout_gross, 2)
                profit = payout_amount - Decimal(str(bet.amount))
                
                # Create transaction record
                external_ref = f"KASOKO-{market.id}-{bet.id}-{timezone.now().timestamp()}"
                
                tx = Transaction.objects.create(
                    user=bet.user,
                    type='PAYOUT',
                    amount=payout_amount,
                    phone_number=normalize_phone(bet.user.phone_number),
                    reference=external_ref,
                    external_ref=external_ref,
                    status=Transaction.PENDING,
                    description=f"Payout for market {market.id}: {market.question}",
                    related_bet=bet
                )
                
                # Update bet record
                bet.payout = payout_amount
                bet.result = 'WON'
                bet.save()
                
                logger.info(
                    f"Bet {bet.id} winner: stake={bet.amount}, payout={payout_amount}, profit={profit}"
                )
                
                # Enqueue B2C call
                if payout_amount >= MIN_PAYOUT:
                    send_b2c_payout.delay(tx.id)
                    payout_count += 1
                else:
                    logger.info(f"Payout {payout_amount} below minimum {MIN_PAYOUT}, marking as failed")
                    tx.status = Transaction.FAILED
                    tx.mpesa_response = {'error': 'payout_below_minimum'}
                    tx.save()
                
                payout_amount_total += payout_amount
            
            # Mark losing bets
            losing_bets = all_bets.exclude(outcome=market.resolved_outcome)
            for bet in losing_bets:
                bet.result = 'LOST'
                bet.save()
            
            # Update market
            market.status = 'RESOLVED'
            market.resolved_at = timezone.now()
            market.save()
            
            return {
                'status': 'settled',
                'market_id': market_id,
                'total_pool': str(total_pool),
                'winners_pool': str(winners_pool),
                'distributable_pool': str(distributable_pool),
                'platform_fee': str(platform_fee_amount),
                'winner_count': winning_bets.count(),
                'loser_count': losing_bets.count(),
                'payout_transactions_created': payout_count,
                'payout_amount_total': str(payout_amount_total)
            }
    
    except Market.DoesNotExist:
        logger.error(f"Market {market_id} not found")
        return {'status': 'error', 'error': 'market_not_found'}
    except Exception as e:
        logger.error(f"Settlement error for market {market_id}: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=5, default_retry_delay=120)
def send_b2c_payout(self, transaction_id):
    """
    Initiate B2C payout call for a payout transaction
    
    Flow:
    1. Fetch transaction
    2. Call B2C API
    3. Store response metadata
    4. Wait for callback to update status
    
    Args:
        transaction_id: Transaction.id of type PAYOUT
    
    Returns:
        dict with B2C response metadata
    """
    try:
        tx = Transaction.objects.get(id=transaction_id, type='PAYOUT')
        
        if tx.status != Transaction.PENDING:
            logger.warning(f"Transaction {transaction_id} already processed, status: {tx.status}")
            return {'status': 'already_processed', 'tx_status': tx.status}
        
        logger.info(f"Initiating B2C payout for transaction {transaction_id}, amount={tx.amount}")
        
        # Call B2C API
        response = call_b2c(tx, tx.user.phone_number, tx.amount)
        
        # Store conversation IDs for callback matching
        tx.mpesa_response = {
            'conversation_id': response.get('ConversationID'),
            'originator_conversation_id': response.get('OriginatorConversationID'),
            'request_id': response.get('RequestId'),
            'response_code': response.get('ResponseCode'),
            'response_description': response.get('ResponseDescription', ''),
        }
        tx.save()
        
        logger.info(
            f"B2C call sent for transaction {transaction_id}, "
            f"conversation_id={response.get('ConversationID')}"
        )
        
        return {
            'status': 'b2c_call_sent',
            'transaction_id': transaction_id,
            'conversation_id': response.get('ConversationID'),
            'response_code': response.get('ResponseCode')
        }
    
    except Transaction.DoesNotExist:
        logger.error(f"Transaction {transaction_id} not found or wrong type")
        return {'status': 'error', 'error': 'transaction_not_found'}
    except Exception as e:
        logger.error(f"B2C payout error for transaction {transaction_id}: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=120 * (2 ** self.request.retries))


@shared_task
def retry_failed_payouts(hours=24):
    """
    Retry failed payout transactions (older than `hours` and marked FAILED)
    Useful for operational recovery from temporary API issues
    
    Args:
        hours: Only retry transactions from the past N hours
    
    Returns:
        dict with retry summary
    """
    from datetime import timedelta
    
    cutoff = timezone.now() - timedelta(hours=hours)
    failed_txs = Transaction.objects.filter(
        type='PAYOUT',
        status=Transaction.FAILED,
        created_at__gte=cutoff,
        mpesa_response__isnull=False
    )
    
    retry_count = 0
    for tx in failed_txs:
        logger.info(f"Retrying failed payout transaction {tx.id}")
        send_b2c_payout.delay(tx.id)
        retry_count += 1
    
    logger.info(f"Enqueued {retry_count} failed payouts for retry")
    return {'status': 'retried', 'count': retry_count}


def _create_refund_transaction(bet):
    """
    Create a refund transaction when no winners in a market
    (Internal helper)
    """
    external_ref = f"KASOKO-REFUND-{bet.id}-{timezone.now().timestamp()}"
    tx = Transaction.objects.create(
        user=bet.user,
        type='PAYOUT',
        amount=Decimal(str(bet.amount)),  # Refund full stake
        phone_number=normalize_phone(bet.user.phone_number),
        reference=external_ref,
        external_ref=external_ref,
        status=Transaction.PENDING,
        description=f"Refund for market {bet.market.id}: {bet.market.question}",
        related_bet=bet
    )
    
    # Enqueue B2C call for refund
    send_b2c_payout.delay(tx.id)
    logger.info(f"Created refund transaction {tx.id} for bet {bet.id}")
