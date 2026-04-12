"""
Audit logging utility for tracking financial and sensitive operations
Simplifies the process of creating audit logs for transactions and events
"""
from audit.models import AuditLog
from django.utils import timezone
import json
import logging

logger = logging.getLogger(__name__)


class AuditLogger:
    """Helper class for creating audit logs"""
    
    @staticmethod
    def log_financial_transaction(
        action, 
        user, 
        amount, 
        content_type,
        object_id,
        before_values=None,
        after_values=None,
        description="",
        ip_address=None,
        user_agent=None,
        related_transaction=None,
        severity='MEDIUM'
    ):
        """
        Log a financial transaction
        
        Args:
            action: Action type (DEPOSIT, WITHDRAWAL, BET_PLACED, PAYOUT_ISSUED, etc.)
            user: User object
            amount: Transaction amount
            content_type: Model name (e.g., 'payments.Transaction')
            object_id: ID of the object (e.g., transaction ID)
            before_values: Dict of values before transaction
            after_values: Dict of values after transaction
            description: Human-readable description
            ip_address: Client IP address
            user_agent: Client user agent
            related_transaction: Reference transaction ID if any
            severity: LOW, MEDIUM, HIGH, CRITICAL
        """
        try:
            changes = {}
            if before_values and after_values:
                for key in after_values:
                    if key not in before_values or before_values[key] != after_values[key]:
                        changes[key] = {
                            'old': str(before_values.get(key)),
                            'new': str(after_values.get(key))
                        }
            
            audit_log = AuditLog.objects.create(
                action=action,
                severity=severity,
                content_type=content_type,
                object_id=str(object_id),
                object_repr=f"{action} - {amount} for {user}",
                user=user,
                ip_address=ip_address,
                user_agent=user_agent or "",
                changes=changes,
                before_values=before_values or {},
                after_values=after_values or {},
                description=description,
                related_transaction=related_transaction or ""
            )
            
            logger.info(
                f"[AUDIT] {action} - User: {user.id}, Amount: {amount}, "
                f"Severity: {severity}, ID: {object_id}"
            )
            
            return audit_log
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
            return None
    
    @staticmethod
    def log_bet_placed(user, bet, market, amount, ip_address=None, user_agent=None):
        """Log when a user places a bet"""
        after_values = {
            'user_id': user.id,
            'market_id': market.id,
            'outcome': bet.outcome,
            'amount': str(amount),
            'entry_probability': bet.entry_probability,
        }
        
        return AuditLogger.log_financial_transaction(
            action='BET_PLACED',
            user=user,
            amount=amount,
            content_type='markets.Bet',
            object_id=bet.id,
            after_values=after_values,
            description=f"User placed {amount} KES bet on market #{market.id}: {market.question}",
            ip_address=ip_address,
            user_agent=user_agent,
            severity='MEDIUM'
        )
    
    @staticmethod
    def log_deposit(user, transaction, amount, ip_address=None, user_agent=None):
        """Log a deposit transaction"""
        before_values = {'balance': '0'}  # Approximate
        after_values = {'balance': str(user.balance), 'amount_deposited': str(amount)}
        
        return AuditLogger.log_financial_transaction(
            action='DEPOSIT',
            user=user,
            amount=amount,
            content_type='payments.Transaction',
            object_id=transaction.id,
            before_values=before_values,
            after_values=after_values,
            description=f"User deposited {amount} KES via M-Pesa",
            ip_address=ip_address,
            user_agent=user_agent,
            related_transaction=transaction.checkout_request_id or "",
            severity='HIGH'
        )
    
    @staticmethod
    def log_withdrawal(user, transaction, amount, ip_address=None, user_agent=None):
        """Log a withdrawal transaction"""
        before_values = {'balance': str(user.balance + amount)}  # Before withdrawal
        after_values = {'balance': str(user.balance)}
        
        return AuditLogger.log_financial_transaction(
            action='WITHDRAWAL',
            user=user,
            amount=amount,
            content_type='payments.Transaction',
            object_id=transaction.id,
            before_values=before_values,
            after_values=after_values,
            description=f"User withdrew {amount} KES",
            ip_address=ip_address,
            user_agent=user_agent,
            related_transaction=transaction.external_ref or "",
            severity='HIGH'
        )
    
    @staticmethod
    def log_payout(user, transaction, amount, market, outcome, ip_address=None):
        """Log a payout to winner"""
        return AuditLogger.log_financial_transaction(
            action='PAYOUT_ISSUED',
            user=user,
            amount=amount,
            content_type='payments.Transaction',
            object_id=transaction.id,
            after_values={'balance': str(user.balance), 'amount': str(amount)},
            description=f"Payout of {amount} KES issued for market resolution: {market.question} ({outcome})",
            ip_address=ip_address,
            related_transaction=transaction.external_ref or "",
            severity='CRITICAL'  # Payouts are critical
        )
    
    @staticmethod
    def log_market_resolution(admin_user, market, outcome, ip_address=None, user_agent=None):
        """Log market resolution by admin"""
        return AuditLogger.log_financial_transaction(
            action='MARKET_RESOLVED',
            user=admin_user,
            amount=0,
            content_type='markets.Market',
            object_id=market.id,
            after_values={'status': 'RESOLVED', 'outcome': outcome},
            description=f"Market resolved: {market.question} - Outcome: {outcome}",
            ip_address=ip_address,
            user_agent=user_agent,
            severity='CRITICAL'
        )
    
    @staticmethod
    def log_kyc_verified(user, ip_address=None, user_agent=None):
        """Log KYC verification"""
        return AuditLogger.log_financial_transaction(
            action='KYC_VERIFIED',
            user=user,
            amount=0,
            content_type='users.CustomUser',
            object_id=user.id,
            after_values={'kyc_verified': True, 'kyc_verified_at': str(timezone.now())},
            description=f"User completed KYC verification",
            ip_address=ip_address,
            user_agent=user_agent,
            severity='MEDIUM'
        )
    
    @staticmethod
    def log_admin_action(admin_user, action_type, target_type, target_id, description, ip_address=None, user_agent=None):
        """Log admin actions"""
        return AuditLogger.log_financial_transaction(
            action='ADMIN_ACTION',
            user=admin_user,
            amount=0,
            content_type=target_type,
            object_id=target_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            severity='HIGH'
        )
    
    @staticmethod
    def log_security_event(action, user, description, ip_address=None, user_agent=None, severity='MEDIUM'):
        """Log security-related events (failed logins, rate limits, etc.)"""
        user_id = user.id if user else None
        user_repr = str(user) if user else "Anonymous"
        
        return AuditLogger.log_financial_transaction(
            action=action,
            user=user,
            amount=0,
            content_type='users.CustomUser',
            object_id=user_id or 'SYSTEM',
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            severity=severity
        )


def get_client_context(request):
    """Extract IP and user agent from request"""
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    ip_address = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
    user_agent = request.headers.get('User-Agent', '')
    
    return ip_address, user_agent
