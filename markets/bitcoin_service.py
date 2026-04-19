import requests
from decimal import Decimal
from .models import Market
import logging
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


class BitcoinPriceService:
    """Service for fetching Bitcoin prices and managing Bitcoin markets"""

    BITCOIN_API_URL = "https://api.coingecko.com/api/v3/simple/price"
    FALLBACK_API_URL = "https://api.binance.com/api/v3/ticker/price"

    @staticmethod
    def get_current_bitcoin_price():
        """
        Fetch current Bitcoin price in USD
        Tries CoinGecko first (no auth needed), falls back to Binance if needed
        Returns: float or None
        """
        try:
            # Try CoinGecko first
            response = requests.get(
                BitcoinPriceService.BITCOIN_API_URL,
                params={'ids': 'bitcoin', 'vs_currencies': 'usd'},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return float(data['bitcoin']['usd'])
        except Exception as e:
            logger.warning(f"CoinGecko API error: {e}")

        # Fallback to Binance
        try:
            response = requests.get(
                BitcoinPriceService.FALLBACK_API_URL,
                params={'symbol': 'BTCUSDT'},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return float(data['price'])
        except Exception as e:
            logger.error(f"Binance API error: {e}")

        return None

    @staticmethod
    def get_bitcoin_market_or_create():
        """Get or create the Bitcoin Up/Down market"""
        # Define end_time as 5 minutes from now
        end_time = timezone.now() + timedelta(minutes=5)

        market, created = Market.objects.get_or_create(
            question="Bitcoin: Up or Down - Next 5 Minutes",
            defaults={
                'category': 'Crypto',
                'description': 'Will the price of Bitcoin go up or down in the next 5 minutes?',
                'market_type': 'BINARY',
                'image_url': 'https://cryptologos.cc/logos/bitcoin-btc-logo.png',
                'yes_probability': 50,
                'volume': 'KES 0',
                'status': 'OPEN',
                'end_date': '5 min',
                'trading_end_time': end_time,
                'b': 100.0,
                'q_yes': 0.0,
                'q_no': 0.0,
                'is_live': True,
            }
        )

        # Update end_time periodically (refresh every time it's requested)
        if not created and market.status == 'OPEN':
            market.trading_end_time = timezone.now() + timedelta(minutes=5)
            market.save(update_fields=['trading_end_time'])

        return market, created

    @staticmethod
    def update_bitcoin_market_price(current_price, previous_price):
        """
        Update market probability based on price movement
        
        Args:
            current_price: Current Bitcoin price in USD
            previous_price: Previous Bitcoin price in USD
            
        Returns:
            int: New yes_probability (1-99)
        """
        if not previous_price or current_price == previous_price:
            return 50

        # Calculate percentage change
        price_change_percent = ((current_price - previous_price) / previous_price) * 100

        # Adjust probability based on price movement
        # More aggressive movement → stronger probability shift
        if price_change_percent > 0:
            # Price going UP = YES (price will be up)
            # Magnify small changes: 0.1% change -> 2% prob shift
            prob_shift = min(25, max(1, int(abs(price_change_percent) * 2)))
            new_probability = min(99, 50 + prob_shift)
        else:
            # Price going DOWN = NO (price will be down)
            prob_shift = min(25, max(1, int(abs(price_change_percent) * 2)))
            new_probability = max(1, 50 - prob_shift)

        return new_probability

    @staticmethod
    def resolve_bitcoin_market(market, resolution: str):
        """
        Resolve an expired Bitcoin market
        
        Args:
            market: Market object
            resolution: 'YES' if price went up, 'NO' if price went down
        """
        if market.status != 'OPEN':
            raise ValueError(f"Cannot resolve market with status {market.status}")

        market.status = 'RESOLVED'
        market.resolved_outcome = resolution
        market.resolved_at = timezone.now()
        market.save(update_fields=['status', 'resolved_outcome', 'resolved_at'])

        logger.info(f"Bitcoin market {market.id} resolved as {resolution}")

    @staticmethod
    def get_bitcoin_market_with_price():
        """
        Get Bitcoin market with current price data
        Returns dict with market data and current Bitcoin price
        """
        market, _ = BitcoinPriceService.get_bitcoin_market_or_create()
        current_price = BitcoinPriceService.get_current_bitcoin_price()

        market_data = {
            'id': market.id,
            'question': market.question,
            'category': market.category,
            'description': market.description,
            'image_url': market.image_url,
            'market_type': market.market_type,
            'yes_probability': market.yes_probability,
            'no_probability': 100 - market.yes_probability,
            'volume': market.volume,
            'status': market.status,
            'end_date': market.end_date,
            'trading_end_time': market.trading_end_time.isoformat() if market.trading_end_time else None,
            'current_bitcoin_price': current_price,
            'current_bitcoin_price_formatted': f"${current_price:,.2f}" if current_price else "N/A",
            'yes_multiplier': round(100 / market.yes_probability, 2) if market.yes_probability > 0 else 0,
            'no_multiplier': round(100 / (100 - market.yes_probability), 2) if market.yes_probability < 100 else 0,
            'q_yes': float(market.q_yes),
            'q_no': float(market.q_no),
            'b': float(market.b),
            'created_at': market.created_at.isoformat(),
            'is_live': market.is_live,
        }

        return market_data
