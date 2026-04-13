"""
Bootstrap initialization functions for LMSR markets.

When a market is created with an initial probability, we need to calculate
the q_yes and q_no values that produce that probability.
"""

import math
from .lmsr import price_yes


def calculate_q_for_probability(probability: float, b: float) -> float:
    """
    Given a desired YES probability and liquidity parameter b,
    calculate the q_yes value needed (assuming q_no = 0 for symmetry).
    
    Formula: q_yes = b * ln(probability / (1 - probability))
    
    This works because when q_no = 0:
        P_yes = exp(q_yes/b) / (exp(q_yes/b) + 1)
        
    Solving for q_yes:
        probability = exp(q_yes/b) / (exp(q_yes/b) + 1)
        probability * (exp(q_yes/b) + 1) = exp(q_yes/b)
        probability * exp(q_yes/b) + probability = exp(q_yes/b)
        probability = exp(q_yes/b) * (1 - probability)
        exp(q_yes/b) = probability / (1 - probability)
        q_yes/b = ln(probability / (1 - probability))
        q_yes = b * ln(probability / (1 - probability))
    
    Args:
        probability: Desired YES probability (0 < p < 1)
        b: Liquidity parameter (default 100)
    
    Returns:
        q_yes value needed
    """
    if probability <= 0 or probability >= 1:
        raise ValueError(f"Probability must be between 0 and 1, got {probability}")
    
    q_yes = b * math.log(probability / (1 - probability))
    return q_yes


def bootstrap_market(initial_probability: float, b: float = 100.0) -> tuple:
    """
    Bootstrap a market with an initial probability.
    
    Args:
        initial_probability: Desired YES probability at market start (0 < p < 1)
        b: Liquidity parameter
    
    Returns:
        (q_yes, q_no) tuple
    """
    q_yes = calculate_q_for_probability(initial_probability, b)
    q_no = 0.0  # By convention, we use q_no = 0 and set q_yes to the desired value
    
    return round(q_yes, 6), round(q_no, 6)


def verify_bootstrap(q_yes: float, q_no: float, b: float, target_probability: float) -> bool:
    """
    Verify that bootstrapped q values produce the expected probability.
    
    Args:
        q_yes: Bootstrapped q_yes
        q_no: Bootstrapped q_no
        b: Liquidity parameter
        target_probability: Expected YES probability
    
    Returns:
        True if close enough (within 0.1%)
    """
    actual_prob = price_yes(q_yes, q_no, b)
    tolerance = 0.001  # 0.1%
    return abs(actual_prob - target_probability) < tolerance
