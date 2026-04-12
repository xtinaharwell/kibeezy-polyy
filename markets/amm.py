"""
Automated Market Maker (AMM) implementation for prediction markets.
Uses constant product formula: YES_reserve * NO_reserve = k (constant)
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Tuple


class AMM:
    """Constant Product Market Maker for binary prediction markets"""
    
    def __init__(self, yes_reserve: Decimal, no_reserve: Decimal):
        """
        Initialize AMM with initial reserves.
        
        Args:
            yes_reserve: Initial reserve of YES shares (in KES value)
            no_reserve: Initial reserve of NO shares (in KES value)
        """
        self.yes_reserve = Decimal(str(yes_reserve))
        self.no_reserve = Decimal(str(no_reserve))
        self.k = self.yes_reserve * self.no_reserve
    
    def get_current_price(self) -> float:
        """
        Get current YES probability (0-100).
        Price = YES_reserve / (YES_reserve + NO_reserve)
        """
        total = self.yes_reserve + self.no_reserve
        if total == 0:
            return 50.0
        
        yes_prob = (self.yes_reserve / total) * 100
        return float(yes_prob.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    def calculate_buy_price(self, amount: Decimal, outcome: str) -> Dict:
        """
        Calculate price and shares received for a buy order.
        
        Args:
            amount: Amount in KES to spend
            outcome: "Yes" or "No"
            
        Returns:
            {
                'shares_received': float, # Shares bought (calculated from opposite reserve change)
                'execution_price': float, # Weighted average price paid (0-100 as probability %)
                'new_yes_probability': float, # Price after trade
                'price_impact': float, # % price change
            }
        """
        amount = Decimal(str(amount))
        current_prob = Decimal(str(self.get_current_price()))
        
        if outcome.lower() == "yes":
            # Buying YES shares
            # You add collateral to YES, withdraw from NO
            old_no_reserve = self.no_reserve
            new_yes_reserve = self.yes_reserve + amount
            new_no_reserve = self.k / new_yes_reserve
            
            # Shares received = reduction in NO reserve (what you extract from the pool)
            shares_received = old_no_reserve - new_no_reserve
            
            # New probability
            total_new = new_yes_reserve + new_no_reserve
            new_prob = (new_yes_reserve / total_new) * 100 if total_new > 0 else 50
            
            # Execution price = weighted average price between old and new
            execution_price = (current_prob + Decimal(str(new_prob))) / Decimal('2')
            
            price_impact = (new_prob - current_prob)
            
            return {
                'shares_received': float(shares_received.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'execution_price': float(execution_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'new_yes_probability': float(new_prob.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'price_impact': float(price_impact.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            }
        else:
            # Buying NO shares
            old_yes_reserve = self.yes_reserve
            new_no_reserve = self.no_reserve + amount
            new_yes_reserve = self.k / new_no_reserve
            
            # Shares received = reduction in YES reserve
            shares_received = old_yes_reserve - new_yes_reserve
            
            # New probability
            total_new = new_yes_reserve + new_no_reserve
            new_prob = (new_yes_reserve / total_new) * 100 if total_new > 0 else 50
            
            # Execution price for NO = 100% - average of YES probabilities
            yes_execution_price = (current_prob + Decimal(str(new_prob))) / Decimal('2')
            execution_price = Decimal('100') - yes_execution_price
            
            price_impact = (new_prob - current_prob)
            
            return {
                'shares_received': float(shares_received.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'execution_price': float(execution_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'new_yes_probability': float(new_prob.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'price_impact': float(price_impact.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            }
    
    def calculate_sell_price(self, shares: Decimal, outcome: str) -> Dict:
        """
        Calculate proceeds for selling shares back to the market.
        
        Args:
            shares: Number of shares to sell
            outcome: "Yes" or "No"
            
        Returns:
            {
                'proceeds': float, # KES received
                'execution_price': float, # Average price received (0-100 as probability %)
                'new_yes_probability': float, # Price after trade
                'price_impact': float, # % price change
            }
        """
        shares = Decimal(str(shares))
        current_prob = Decimal(str(self.get_current_price()))
        
        if outcome.lower() == "yes":
            # Selling YES shares (reducing YES reserve)
            new_yes_reserve = self.yes_reserve - shares
            if new_yes_reserve <= 0:
                raise ValueError("Cannot sell more YES shares than in reserve")
            
            new_no_reserve = self.k / new_yes_reserve
            
            # Proceeds = difference in NO reserve (what you receive from the pool)
            proceeds = new_no_reserve - self.no_reserve
            
            # New probability
            total_new = new_yes_reserve + new_no_reserve
            new_prob = (new_yes_reserve / total_new) * 100 if total_new > 0 else 50
            
            # Execution price = weighted average between old and new YES probability
            execution_price = (current_prob + Decimal(str(new_prob))) / Decimal('2')
            
            price_impact = (new_prob - current_prob)
            
            return {
                'proceeds': float(proceeds.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'execution_price': float(execution_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'new_yes_probability': float(new_prob.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'price_impact': float(price_impact.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            }
        else:
            # Selling NO shares
            new_no_reserve = self.no_reserve - shares
            if new_no_reserve <= 0:
                raise ValueError("Cannot sell more NO shares than in reserve")
            
            new_yes_reserve = self.k / new_no_reserve
            proceeds = new_yes_reserve - self.yes_reserve
            
            total_new = new_yes_reserve + new_no_reserve
            new_prob = (new_yes_reserve / total_new) * 100 if total_new > 0 else 50
            
            # Execution price for NO = 100% - average of YES probabilities
            yes_execution_price = (current_prob + Decimal(str(new_prob))) / Decimal('2')
            execution_price = Decimal('100') - yes_execution_price
            
            price_impact = (new_prob - current_prob)
            
            return {
                'proceeds': float(proceeds.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'execution_price': float(execution_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'new_yes_probability': float(new_prob.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'price_impact': float(price_impact.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            }
    
    def update_reserves(self, outcome: str, amount: Decimal, is_buy: bool = True):
        """
        Update reserves after a trade. Used to persist changes to database.
        
        Args:
            outcome: "Yes" or "No"
            amount: Amount of KES or shares involved
            is_buy: True for buy, False for sell
            
        Returns:
            (new_yes_reserve, new_no_reserve)
        """
        amount = Decimal(str(amount))
        
        if is_buy:
            if outcome.lower() == "yes":
                new_yes_reserve = self.yes_reserve + amount
                new_no_reserve = self.k / new_yes_reserve
            else:
                new_no_reserve = self.no_reserve + amount
                new_yes_reserve = self.k / new_no_reserve
        else:
            # Sell: amount is shares
            if outcome.lower() == "yes":
                new_yes_reserve = self.yes_reserve - amount
            else:
                new_no_reserve = self.no_reserve - amount
            
            if outcome.lower() == "yes":
                new_no_reserve = self.k / new_yes_reserve
            else:
                new_yes_reserve = self.k / new_no_reserve
        
        self.yes_reserve = new_yes_reserve
        self.no_reserve = new_no_reserve
        return (new_yes_reserve, new_no_reserve)
