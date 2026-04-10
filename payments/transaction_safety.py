"""
Transaction Safety Module - Database Integrity & Atomicity

Ensures all financial operations are atomic and consistent.
Provides utilities for safe transaction processing and verification.
"""

import logging
from decimal import Decimal
from django.db import transaction as db_transaction
from django.db.models import Sum
from django.utils import timezone
from .models import Transaction
from users.models import CustomUser

logger = logging.getLogger(__name__)


class TransactionError(Exception):
    """Custom exception for transaction processing errors"""
    pass


def safe_process_deposit(user: CustomUser, amount: Decimal, 
                        external_ref: str, transaction_type: str = 'DEPOSIT',
                        mpesa_response: dict = None, **additional_fields) -> Transaction:
    """
    Safely process a deposit with atomic transaction guarantee.
    
    Both the balance update AND transaction record are created together,
    or both are rolled back if any error occurs.
    
    Args:
        user: CustomUser instance
        amount: Decimal amount to deposit
        external_ref: External reference from payment provider
        transaction_type: Type of transaction (DEPOSIT, WITHDRAWAL, PAYOUT, BET)
        mpesa_response: M-Pesa response data (optional)
        **additional_fields: Additional fields for Transaction record
    
    Returns:
        Transaction object created
    
    Raises:
        TransactionError: If operation fails
    """
    try:
        with db_transaction.atomic():
            # Verify user is valid and active
            if not user.is_active:
                raise TransactionError(f"User {user.id} account is inactive")
            
            # Verify amount is positive
            if amount <= 0:
                raise TransactionError(f"Amount must be positive, got {amount}")
            
            # Create transaction record
            txn = Transaction.objects.create(
                user=user,
                type=transaction_type,
                amount=amount,
                phone_number=user.phone_number,
                external_ref=external_ref,
                status='COMPLETED',
                mpesa_response=mpesa_response or {},
                **additional_fields
            )
            
            # Update user balance atomically
            user.balance += amount
            user.save(update_fields=['balance'])
            
            logger.info(
                f"✓ Deposit processed atomically: user={user.id}, "
                f"amount={amount}, tx_id={txn.id}, new_balance={user.balance}"
            )
            
            return txn
            
    except TransactionError as e:
        logger.error(f"✗ Transaction failed: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"✗ Unexpected error in deposit: {str(e)}")
        raise TransactionError(f"Failed to process deposit: {str(e)}")


def safe_process_withdrawal(user: CustomUser, amount: Decimal,
                           external_ref: str, mpesa_response: dict = None,
                           **additional_fields) -> Transaction:
    """
    Safely process a withdrawal with balance verification.
    
    Ensures user has sufficient funds before deducting balance.
    Both operations are atomic.
    
    Args:
        user: CustomUser instance
        amount: Decimal amount to withdraw
        external_ref: External reference from payment provider
        mpesa_response: M-Pesa response data (optional)
        **additional_fields: Additional fields for Transaction record
    
    Returns:
        Transaction object created
    
    Raises:
        TransactionError: If operation fails or insufficient balance
    """
    try:
        with db_transaction.atomic():
            # Fetch fresh user data to ensure consistency
            user = CustomUser.objects.select_for_update().get(id=user.id)
            
            # Verify sufficient balance
            if user.balance < amount:
                raise TransactionError(
                    f"Insufficient balance: {user.balance} < {amount}"
                )
            
            # Create transaction record BEFORE deducting balance
            txn = Transaction.objects.create(
                user=user,
                type='WITHDRAWAL',
                amount=amount,
                phone_number=user.phone_number,
                external_ref=external_ref,
                status='COMPLETED',
                mpesa_response=mpesa_response or {},
                **additional_fields
            )
            
            # Deduct balance atomically
            user.balance -= amount
            user.save(update_fields=['balance'])
            
            logger.info(
                f"✓ Withdrawal processed atomically: user={user.id}, "
                f"amount={amount}, tx_id={txn.id}, new_balance={user.balance}"
            )
            
            return txn
            
    except TransactionError as e:
        logger.error(f"✗ Withdrawal failed: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"✗ Unexpected error in withdrawal: {str(e)}")
        raise TransactionError(f"Failed to process withdrawal: {str(e)}")


def verify_transaction_immutability(transaction_id: int) -> bool:
    """
    Verify that a transaction record hasn't been tampered with.
    
    Checks if the transaction was created with current data
    and hasn't been modified.
    
    Args:
        transaction_id: ID of transaction to verify
    
    Returns:
        True if verified, False otherwise
    """
    try:
        txn = Transaction.objects.get(id=transaction_id)
        
        # Transaction should have created_at and updated_at
        if not txn.created_at:
            logger.warning(f"Transaction {transaction_id} has no created_at timestamp")
            return False
        
        # Check if modified (updated_at > created_at + 1 minute)
        time_diff = txn.updated_at - txn.created_at
        if time_diff.total_seconds() > 60:  # More than 1 minute difference
            logger.warning(
                f"Transaction {transaction_id} was modified after creation "
                f"(diff: {time_diff.total_seconds()}s)"
            )
            return False
        
        # Verify required fields exist
        if not txn.user or not txn.amount or not txn.external_ref:
            logger.warning(f"Transaction {transaction_id} missing required fields")
            return False
        
        logger.info(f"✓ Transaction {transaction_id} verified as immutable")
        return True
        
    except Transaction.DoesNotExist:
        logger.error(f"Transaction {transaction_id} not found")
        return False


def verify_user_balance_consistency(user_id: int) -> dict:
    """
    Verify user's balance is consistent with transaction history.
    
    Calculates expected balance from transaction log and compares
    with actual balance in user record.
    
    Args:
        user_id: ID of user to verify
    
    Returns:
        Dictionary with verification results:
        {
            'is_consistent': bool,
            'expected_balance': Decimal,
            'actual_balance': Decimal,
            'difference': Decimal,
            'total_deposits': Decimal,
            'total_withdrawals': Decimal,
            'deposit_count': int,
            'withdrawal_count': int
        }
    """
    try:
        user = CustomUser.objects.get(id=user_id)
        
        # Calculate totals from transaction history
        deposits = Transaction.objects.filter(
            user=user,
            type='DEPOSIT',
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        withdrawals = Transaction.objects.filter(
            user=user,
            type__in=['WITHDRAWAL', 'BET'],
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        expected_balance = deposits - withdrawals
        actual_balance = user.balance
        difference = actual_balance - expected_balance
        
        is_consistent = difference == 0
        
        result = {
            'is_consistent': is_consistent,
            'expected_balance': float(expected_balance),
            'actual_balance': float(actual_balance),
            'difference': float(difference),
            'total_deposits': float(deposits),
            'total_withdrawals': float(withdrawals),
            'deposit_count': Transaction.objects.filter(
                user=user, type='DEPOSIT', status='COMPLETED'
            ).count(),
            'withdrawal_count': Transaction.objects.filter(
                user=user, type__in=['WITHDRAWAL', 'BET'], status='COMPLETED'
            ).count()
        }
        
        if is_consistent:
            logger.info(f"✓ User {user_id} balance verified: ${actual_balance}")
        else:
            logger.warning(
                f"⚠ User {user_id} balance inconsistency detected: "
                f"expected ${expected_balance}, got ${actual_balance}, "
                f"difference: ${difference}"
            )
        
        return result
        
    except CustomUser.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'error': 'User not found'}


def create_atomic_bet_transaction(user: CustomUser, amount: Decimal,
                                 market_id: int, external_ref: str = None) -> Transaction:
    """
    Atomically deduct bet amount from user balance and create bet transaction.
    
    Args:
        user: CustomUser instance
        amount: Amount to deduct for bet
        market_id: Market ID this bet is for
        external_ref: Optional external reference
    
    Returns:
        Transaction object created
    
    Raises:
        TransactionError: If operation fails
    """
    return safe_process_withdrawal(
        user=user,
        amount=amount,
        external_ref=external_ref or f"BET-{market_id}-{timezone.now().timestamp()}",
        description=f"Bet placed on market {market_id}",
        transaction_type='BET'
    )


def rollback_failed_transaction(transaction_id: int, reason: str = "") -> bool:
    """
    Safely reverse a failed transaction by restoring user balance.
    
    Creates a new PAYOUT transaction to reverse the effect.
    
    Args:
        transaction_id: ID of transaction to reverse
        reason: Reason for rollback
    
    Returns:
        True if successful, False otherwise
    """
    try:
        original_txn = Transaction.objects.get(id=transaction_id)
        
        if original_txn.status != 'FAILED':
            logger.warning(
                f"Cannot rollback transaction {transaction_id}: "
                f"status is {original_txn.status}, not FAILED"
            )
            return False
        
        # Create reverse transaction
        reverse_txn = safe_process_deposit(
            user=original_txn.user,
            amount=original_txn.amount,
            external_ref=f"ROLLBACK-{transaction_id}",
            transaction_type='PAYOUT',
            description=f"Rollback of failed transaction {transaction_id}. Reason: {reason}"
        )
        
        logger.info(
            f"✓ Transaction {transaction_id} rolled back, "
            f"reverse transaction created: {reverse_txn.id}"
        )
        
        return True
        
    except Transaction.DoesNotExist:
        logger.error(f"Transaction {transaction_id} not found for rollback")
        return False
    except TransactionError as e:
        logger.error(f"Failed to rollback transaction {transaction_id}: {str(e)}")
        return False
