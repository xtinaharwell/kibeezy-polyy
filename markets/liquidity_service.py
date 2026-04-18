"""
Liquidity Provider (LP) Service Layer

Handles all operations for the Simple Fee Distribution model:
- Depositing capital into liquidity pools
- Withdrawing liquidity
- Distributing trading fees to LPs
- Claiming accumulated fees

Phase 1 Implementation: All fees split equally among LPs
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .models import (
    Market,
    LiquidityPool,
    LiquidityProvider,
    FeeDistribution,
    Bet,
)
from .lmsr import (
    price_yes as calc_price_yes,
    price_no as calc_price_no,
    cost as calc_cost,
)

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Liquidity parameters
DEFAULT_LIQUIDITY_PARAMETER_B = 100.0

# Fee structure  
TRADING_FEE_PERCENT = 0.5  # 0.5% on every trade
WITHDRAWAL_FEE_PERCENT = 0.1  # 0.1% on withdrawal
EARLY_WITHDRAWAL_PENALTY = 0.02  # 2% if withdrawn within 7 days

EARLY_WITHDRAWAL_LOCKUP_DAYS = 7  # Lockup period for penalty-free withdrawal

# Payout per share (must match trading constants)
PAYOUT_PER_SHARE = 100


# ============================================================================
# LIQUIDITY POOL INITIALIZATION
# ============================================================================

def initialize_liquidity_pool(market: Market) -> LiquidityPool:
    """
    Initialize a new liquidity pool for a market.
    Called automatically when market is created.
    
    Args:
        market: Market instance
    
    Returns:
        LiquidityPool instance
    """
    pool, created = LiquidityPool.objects.get_or_create(
        market=market,
        defaults={
            'fee_percent': TRADING_FEE_PERCENT,
            'withdrawal_fee_percent': WITHDRAWAL_FEE_PERCENT,
            'early_withdrawal_penalty': EARLY_WITHDRAWAL_PENALTY,
        }
    )
    return pool


# ============================================================================
# DEPOSITS & WITHDRAWALS
# ============================================================================

@transaction.atomic
def deposit_liquidity(
    market: Market,
    user,
    amount_kes: float,
) -> dict:
    """
    User deposits capital into the liquidity pool.
    
    Strategy: Deposit capital split 50/50 into YES/NO at current market price.
    This is "market-neutral" - LP is not betting on outcome, just earning fees.
    
    Args:
        market: Market instance
        user: User depositing liquidity
        amount_kes: Amount in KES to deposit
    
    Returns:
        {
            'success': bool,
            'lp_provider': LiquidityProvider,
            'yes_shares': float,
            'no_shares': float,
            'capital_provided': float,
            'message': str,
        }
    """
    if amount_kes <= 0:
        return {
            'success': False,
            'message': 'Deposit amount must be positive',
        }
    
    # Get or create pool
    pool = initialize_liquidity_pool(market)
    
    # Get current market price
    q_yes = float(market.q_yes)
    q_no = float(market.q_no)
    b = float(market.b)
    
    p_yes = calc_price_yes(q_yes, q_no, b)
    p_no = calc_price_no(q_yes, q_no, b)
    
    # Split capital 50/50
    half_capital = amount_kes / 2
    
    # Calculate shares to buy at current prices
    # Cost = shares * probability * 100 (PAYOUT_PER_SHARE)
    yes_shares = half_capital / (p_yes * PAYOUT_PER_SHARE)
    no_shares = half_capital / (p_no * PAYOUT_PER_SHARE)
    
    # Get or create LP provider record
    lp_provider, created = LiquidityProvider.objects.get_or_create(
        user=user,
        pool=pool,
        defaults={
            'capital_provided': Decimal(str(amount_kes)),
            'yes_shares_owned': 0.0,
            'no_shares_owned': 0.0,
        }
    )
    
    # If LP already has position, add to it
    if not created:
        lp_provider.capital_provided += Decimal(str(amount_kes))
    
    # Update LP's share ownership
    lp_provider.yes_shares_owned += yes_shares
    lp_provider.no_shares_owned += no_shares
    lp_provider.save()
    
    # Update pool's total shares
    pool.total_yes_shares += yes_shares
    pool.total_no_shares += no_shares
    pool.save()
    
    return {
        'success': True,
        'lp_provider': lp_provider,
        'yes_shares': yes_shares,
        'no_shares': no_shares,
        'capital_provided': float(lp_provider.capital_provided),
        'lp_share_percent': lp_provider.lp_share_percent,
        'message': f'Successfully deposited {amount_kes} KES. Received {yes_shares:.4f} YES + {no_shares:.4f} NO shares.',
    }


@transaction.atomic
def withdraw_liquidity(lp_provider: LiquidityProvider) -> dict:
    """
    Withdraw all liquidity from pool with associated fees.
    
    Charges:
    - Withdrawal fee: 0.1% of withdrawal amount
    - Early withdrawal penalty: 2% if withdrawn within 7 days
    
    Args:
        lp_provider: LiquidityProvider instance to withdraw
    
    Returns:
        {
            'success': bool,
            'withdrawal_amount_kes': float,
            'fees_earned': float,
            'withdrawal_fee': float,
            'early_penalty': float,
            'net_amount': float,
            'message': str,
        }
    """
    pool = lp_provider.pool
    market = pool.market
    
    q_yes = float(market.q_yes)
    q_no = float(market.q_no)
    b = float(market.b)
    
    p_yes = calc_price_yes(q_yes, q_no, b)
    p_no = calc_price_no(q_yes, q_no, b)
    
    # Calculate current value of shares
    yes_value = lp_provider.yes_shares_owned * p_yes * PAYOUT_PER_SHARE
    no_value = lp_provider.no_shares_owned * p_no * PAYOUT_PER_SHARE
    total_shares_value = yes_value + no_value
    
    # Apply withdrawal fees
    withdrawal_fee = (total_shares_value * pool.withdrawal_fee_percent) / 100
    
    # Check for early withdrawal penalty
    days_invested = (timezone.now() - lp_provider.entry_date).days
    early_penalty = 0
    if days_invested < EARLY_WITHDRAWAL_LOCKUP_DAYS:
        early_penalty = (total_shares_value * pool.early_withdrawal_penalty) / 100
    
    # Net amount after fees
    net_withdrawal = total_shares_value - withdrawal_fee - early_penalty
    
    # Add any unclaimed fees
    fees_available = lp_provider.total_available_claimable
    total_payout = net_withdrawal + float(fees_available)
    
    # Update pool - remove shares
    pool.total_yes_shares -= lp_provider.yes_shares_owned
    pool.total_no_shares -= lp_provider.no_shares_owned
    pool.save()
    
    # Mark LP provider as withdrawn (delete record)
    lp_provider.delete()
    
    return {
        'success': True,
        'withdrawal_amount_kes': total_shares_value,
        'fees_earned': float(lp_provider.total_fees_earned),
        'withdrawal_fee': withdrawal_fee,
        'early_penalty': early_penalty,
        'net_amount': total_payout,
        'days_invested': days_invested,
        'message': f'Withdrawal complete. Received {total_payout:.2f} KES (shares: {net_withdrawal:.2f}, fees: {fees_available:.2f}, penalties: {withdrawal_fee + early_penalty:.2f})',
    }


# ============================================================================
# FEE DISTRIBUTION (Called when trades execute)
# ============================================================================

@transaction.atomic
def distribute_trading_fee(pool: LiquidityPool, fee_amount_kes: float, source_bet: Bet = None) -> dict:
    """
    Distribute a trading fee to all liquidity providers equally.
    
    Called after every trade by the trading service.
    
    Args:
        pool: LiquidityPool instance
        fee_amount_kes: Amount of fee to distribute
        source_bet: The Bet that generated this fee (optional, for audit trail)
    
    Returns:
        {
            'success': bool,
            'num_providers': int,
            'per_provider_fee': float,
            'message': str,
        }
    """
    providers = pool.providers.all()
    
    if not providers.exists():
        # No LPs in pool yet, fee is not distributed
        return {
            'success': False,
            'num_providers': 0,
            'message': 'No liquidity providers in pool',
        }
    
    num_providers = providers.count()
    per_provider_fee = fee_amount_kes / num_providers
    
    # Distribute fee to each LP equally
    for provider in providers:
        provider.total_fees_earned += Decimal(str(per_provider_fee))
        provider.unclaimed_fees += Decimal(str(per_provider_fee))
        provider.last_fee_update = timezone.now()
        provider.save()
        
        # Create audit trail
        FeeDistribution.objects.create(
            pool=pool,
            provider=provider,
            fee_amount=Decimal(str(per_provider_fee)),
            source_bet=source_bet,
            is_claimed=False,
        )
    
    # Update pool totals
    pool.total_fees_collected += Decimal(str(fee_amount_kes))
    pool.total_unclaimed_fees += Decimal(str(fee_amount_kes))
    pool.save()
    
    return {
        'success': True,
        'num_providers': num_providers,
        'per_provider_fee': per_provider_fee,
        'total_distributed': fee_amount_kes,
        'message': f'Fee {fee_amount_kes:.2f} KES distributed to {num_providers} providers',
    }


# ============================================================================
# FEE CLAIMING
# ============================================================================

@transaction.atomic
def claim_fees(lp_provider: LiquidityProvider) -> dict:
    """
    LP claims accumulated fees.
    
    Updates their fees_claimed and clears unclaimed_fees.
    In production, this would trigger a payment to user's wallet/account.
    
    Args:
        lp_provider: LiquidityProvider instance
    
    Returns:
        {
            'success': bool,
            'amount_claimed': float,
            'remaining_balance': float,
            'message': str,
        }
    """
    if lp_provider.unclaimed_fees <= 0:
        return {
            'success': False,
            'amount_claimed': 0,
            'remaining_balance': 0,
            'message': 'No fees to claim',
        }
    
    amount_to_claim = float(lp_provider.unclaimed_fees)
    
    # Update the provider
    lp_provider.fees_claimed += lp_provider.unclaimed_fees
    lp_provider.unclaimed_fees = Decimal('0')
    lp_provider.save()
    
    # Mark distributions as claimed
    FeeDistribution.objects.filter(
        provider=lp_provider,
        is_claimed=False,
    ).update(
        is_claimed=True,
        claimed_at=timezone.now(),
    )
    
    # In a real system, this would trigger payment processing (M-Pesa withdrawal, etc.)
    # For now, just return the data
    
    return {
        'success': True,
        'amount_claimed': amount_to_claim,
        'remaining_balance': float(lp_provider.total_available_claimable),
        'message': f'Successfully claimed {amount_to_claim:.2f} KES in fees',
    }


# ============================================================================
# POOL STATISTICS & INSIGHTS
# ============================================================================

def get_pool_stats(pool: LiquidityPool) -> dict:
    """
    Get current statistics for a liquidity pool.
    
    Returns:
        {
            'market_id': int,
            'market_question': str,
            'num_providers': int,
            'total_unclaimed_fees': float,
            'total_fees_collected': float,
            'total_liquidity_yes_shares': float,
            'total_liquidity_no_shares': float,
            'fee_percent': float,
            'providers': [...]
        }
    """
    providers = pool.providers.all()
    
    provider_data = []
    for provider in providers:
        provider_data.append({
            'user_id': provider.user.id,
            'user_phone': provider.user.phone_number if hasattr(provider.user, 'phone_number') else 'N/A',
            'lp_share_percent': provider.lp_share_percent,
            'yes_shares': provider.yes_shares_owned,
            'no_shares': provider.no_shares_owned,
            'total_fees_earned': float(provider.total_fees_earned),
            'unclaimed_fees': float(provider.unclaimed_fees),
            'entry_date': provider.entry_date.isoformat(),
        })
    
    return {
        'market_id': pool.market.id,
        'market_question': pool.market.question,
        'num_providers': providers.count(),
        'total_unclaimed_fees': float(pool.total_unclaimed_fees),
        'total_fees_collected': float(pool.total_fees_collected),
        'total_liquidity_yes_shares': pool.total_yes_shares,
        'total_liquidity_no_shares': pool.total_no_shares,
        'fee_percent': pool.fee_percent,
        'withdrawal_fee_percent': pool.withdrawal_fee_percent,
        'early_withdrawal_penalty': pool.early_withdrawal_penalty,
        'providers': provider_data,
    }


def get_lp_performance(lp_provider: LiquidityProvider) -> dict:
    """
    Get detailed performance metrics for a single LP.
    
    Returns:
        {
            'user': str,
            'market': str,
            'capital_provided': float,
            'days_invested': int,
            'total_fees_earned': float,
            'unclaimed_fees': float,
            'fees_claimed': float,
            'lp_share_percent': float,
            'estimated_apy': float,
            'yes_shares': float,
            'no_shares': float,
        }
    """
    days_invested = max(1, (timezone.now() - lp_provider.entry_date).days)
    
    # Calculate simple APY
    fees_earned = float(lp_provider.total_fees_earned)
    annualized_fees = (fees_earned / days_invested) * 365
    capital = float(lp_provider.capital_provided)
    estimated_apy = (annualized_fees / capital * 100) if capital > 0 else 0
    
    return {
        'user': lp_provider.user.phone_number if hasattr(lp_provider.user, 'phone_number') else str(lp_provider.user),
        'market': lp_provider.pool.market.question[:60],
        'capital_provided': capital,
        'days_invested': days_invested,
        'total_fees_earned': fees_earned,
        'unclaimed_fees': float(lp_provider.unclaimed_fees),
        'fees_claimed': float(lp_provider.fees_claimed),
        'lp_share_percent': lp_provider.lp_share_percent,
        'estimated_apy': estimated_apy,
        'yes_shares': lp_provider.yes_shares_owned,
        'no_shares': lp_provider.no_shares_owned,
    }
