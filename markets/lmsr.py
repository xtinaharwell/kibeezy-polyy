"""
Logarithmic Market Scoring Rule (LMSR) implementation.

LMSR is a market maker mechanism that:
1. Maintains a cost function: C(q_yes, q_no) = b * log(exp(q_yes/b) + exp(q_no/b))
2. Derives prices from the cost function derivatives
3. Ensures YES + NO probabilities always sum to 1
4. Has bounded loss for the market maker
"""

import math


def cost(q_yes: float, q_no: float, b: float) -> float:
    """
    Calculate the total cost (or wealth) of the market.
    
    Formula: C(q_yes, q_no) = b * ln(exp(q_yes/b) + exp(q_no/b))
    
    Args:
        q_yes: YES quantity issued
        q_no: NO quantity issued
        b: Liquidity parameter (higher = more liquidity, less price impact)
    
    Returns:
        Total cost in KES (when multiplied by share value 100)
    """
    try:
        exp_yes = math.exp(q_yes / b)
        exp_no = math.exp(q_no / b)
        return b * math.log(exp_yes + exp_no)
    except (ValueError, OverflowError):
        # Handle extreme values gracefully
        return b * max(q_yes, q_no) / b + b


def price_yes(q_yes: float, q_no: float, b: float) -> float:
    """
    Calculate the current YES price (probability).
    
    Formula: P_yes = exp(q_yes/b) / (exp(q_yes/b) + exp(q_no/b))
    
    Args:
        q_yes: YES quantity issued
        q_no: NO quantity issued
        b: Liquidity parameter
    
    Returns:
        Price as probability between 0 and 1
    """
    try:
        exp_yes = math.exp(q_yes / b)
        exp_no = math.exp(q_no / b)
        return exp_yes / (exp_yes + exp_no)
    except (ValueError, OverflowError):
        # Handle extreme deviations
        if q_yes > q_no:
            return 0.999
        elif q_no > q_yes:
            return 0.001
        return 0.5


def price_no(q_yes: float, q_no: float, b: float) -> float:
    """
    Calculate the current NO price (probability).
    
    Formula: P_no = 1 - P_yes
    
    Args:
        q_yes: YES quantity issued
        q_no: NO quantity issued
        b: Liquidity parameter
    
    Returns:
        Price as probability between 0 and 1
    """
    return 1.0 - price_yes(q_yes, q_no, b)


def calculate_cost_to_buy_shares(
    q_yes_before: float,
    q_no_before: float,
    shares: float,
    outcome: str,
    b: float
) -> float:
    """
    Calculate the KES cost to buy a given quantity of shares.
    
    Cost = (C_after - C_before) * 100
    where C is the cost function and 100 is the share value in KES.
    
    Args:
        q_yes_before: YES quantity before trade
        q_no_before: NO quantity before trade
        shares: Number of shares to buy
        outcome: "YES" or "NO"
        b: Liquidity parameter
    
    Returns:
        Cost in KES
    """
    if outcome.upper() == "YES":
        q_yes_after = q_yes_before + shares
        q_no_after = q_no_before
    else:
        q_yes_after = q_yes_before
        q_no_after = q_no_before + shares
    
    cost_before = cost(q_yes_before, q_no_before, b)
    cost_after = cost(q_yes_after, q_no_after, b)
    
    # Cost difference multiplied by share value (100 KES per share)
    cost_kes = (cost_after - cost_before) * 100
    return round(cost_kes, 2)


def calculate_payout_from_selling(
    q_yes_before: float,
    q_no_before: float,
    shares: float,
    outcome: str,
    b: float
) -> float:
    """
    Calculate the KES payout from selling shares back to the market.
    
    Payout = (C_before - C_after) * 100
    where C is the cost function.
    
    Args:
        q_yes_before: YES quantity before trade
        q_no_before: NO quantity before trade
        shares: Number of shares to sell
        outcome: "YES" or "NO"
        b: Liquidity parameter
    
    Returns:
        Payout in KES
    """
    if outcome.upper() == "YES":
        q_yes_after = q_yes_before - shares
        q_no_after = q_no_before
    else:
        q_yes_after = q_yes_before
        q_no_after = q_no_before - shares
    
    cost_before = cost(q_yes_before, q_no_before, b)
    cost_after = cost(q_yes_after, q_no_after, b)
    
    # Payout is the difference
    payout_kes = (cost_before - cost_after) * 100
    return round(payout_kes, 2)
 
    # Add TRADING FEES
