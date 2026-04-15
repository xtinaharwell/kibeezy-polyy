"""
Test script to verify SELL orders with fractional shares work correctly
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kibeezy.settings')
django.setup()

from django.contrib.auth import get_user_model
from markets.models import Market, Bet
from users.models import CustomUser
from datetime import timedelta, datetime
from django.utils import timezone

User = get_user_model()

def test_fractional_sell_order():
    """Test that SELL orders with fractional shares (8.51237660) work"""
    print("\n" + "="*70)
    print("TEST: SELL Order with Fractional Shares")
    print("="*70)
    
    # Create test user
    try:
        user = User.objects.get(username='test_fractional_user')
        user.delete()
    except User.DoesNotExist:
        pass
    
    user = User.objects.create_user(
        username='test_fractional_user',
        email='test_fractional@test.com',
        password='testpass123'
    )
    user.balance = Decimal('10000.00')
    user.save()
    print(f"✓ Created test user: {user.username} with balance KES {user.balance}")
    
    # Create test market
    try:
        market = Market.objects.get(question='Test Market for Fractional Shares')
        market.delete()
    except Market.DoesNotExist:
        pass
    
    market = Market.objects.create(
        question='Test Market for Fractional Shares',
        description='test',
        status='OPEN',
        yes_probability=50,
        q_yes=Decimal('1000'),
        q_no=Decimal('1000'),
        b=Decimal('1000'),
        market_type='BINARY'
    )
    print(f"✓ Created test market: {market.question}")
    
    # First, create a BUY order to give the user shares
    buy_bet = Bet.objects.create(
        user=user,
        market=market,
        outcome='Yes',
        amount=Decimal('1500.00'),  # KES amount for BUY
        entry_probability=50,
        quantity=Decimal('30'),  # 30 shares of Yes
        action='BUY',
        order_type='MARKET',
        order_status='FILLED'
    )
    print(f"✓ Created BUY bet: {buy_bet.quantity} shares for KES {buy_bet.amount}")
    
    # Now create a SELL order with fractional shares (8.51237660)
    fractional_amount = Decimal('8.51237660')
    print(f"\nAttempting to create SELL order with {fractional_amount} shares...")
    
    try:
        sell_bet = Bet.objects.create(
            user=user,
            market=market,
            outcome='Yes',
            amount=fractional_amount,  # Shares for SELL
            entry_probability=50,
            quantity=fractional_amount,  # Same as amount for SELL
            action='SELL',
            order_type='LIMIT',
            limit_price=Decimal('50.00'),
            order_status='PENDING'
        )
        print(f"✓ SUCCESS! Created SELL bet with {sell_bet.amount} shares")
        print(f"  - Amount: {sell_bet.amount}")
        print(f"  - Quantity: {sell_bet.quantity}")
        print(f"  - Amount decimal places: {sell_bet.amount.as_tuple().exponent}")
        return True
    except Exception as e:
        print(f"✗ FAILED to create SELL bet: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_fractional_sell_order()
    print("\n" + "="*70)
    if success:
        print("✓ Test PASSED: Fractional SELL orders are working!")
    else:
        print("✗ Test FAILED: Fractional SELL orders are still blocked")
    print("="*70)
