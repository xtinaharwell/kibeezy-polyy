"""
Daily balance reconciliation command.

Verifies that user balances match the sum of their transactions.
Alerts on discrepancies.

Usage:
    python manage.py reconcile_balances
    python manage.py reconcile_balances --user-id=123
    python manage.py reconcile_balances --alert-only
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum
from decimal import Decimal
import logging
from payments.transaction_safety import verify_user_balance_consistency
from users.models import CustomUser
from payments.models import Transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reconcile user balances with transaction history'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Reconcile specific user by ID'
        )
        parser.add_argument(
            '--alert-only',
            action='store_true',
            help='Only show discrepancies, do not reconcile'
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix discrepancies (use with caution)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('BALANCE RECONCILIATION REPORT'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
        
        user_id = options['user_id']
        alert_only = options['alert_only']
        fix = options['fix']
        
        if user_id:
            users = CustomUser.objects.filter(id=user_id)
            if not users.exists():
                raise CommandError(f'User with ID {user_id} not found')
        else:
            users = CustomUser.objects.all()
        
        total_discrepancies = 0
        fixed_count = 0
        
        for user in users:
            result = verify_user_balance_consistency(user.id)
            
            if not result['is_consistent']:
                total_discrepancies += 1
                
                self.stdout.write(self.style.WARNING(
                    f"\n⚠️  DISCREPANCY FOUND - User {user.id} ({user.phone_number})"
                ))
                self.stdout.write(f"  Expected Balance: KES {result['expected_balance']}")
                self.stdout.write(f"  Actual Balance:   KES {result['actual_balance']}")
                self.stdout.write(self.style.ERROR(
                    f"  Difference:       KES {result['difference']}"
                ))
                self.stdout.write(f"  Total Deposits:    {result['deposit_count']} (KES {result['total_deposits']})")
                self.stdout.write(f"  Total Withdrawals: {result['withdrawal_count']} (KES {result['total_withdrawals']})")
                
                # Offer to fix if flag is set
                if fix and not alert_only:
                    try:
                        user.balance = Decimal(str(result['expected_balance']))
                        user.save(update_fields=['balance'])
                        
                        # Log correction
                        Transaction.objects.create(
                            user=user,
                            type='PAYOUT',
                            amount=abs(Decimal(str(result['difference']))),
                            phone_number=user.phone_number,
                            status='COMPLETED',
                            description=f"Reconciliation correction: balance adjusted by {result['difference']}",
                            external_ref=f"RECONCILE-{user.id}"
                        )
                        
                        logger.info(f"✓ Fixed balance for user {user.id}: {result['difference']}")
                        self.stdout.write(self.style.SUCCESS("  ✓ Balance corrected"))
                        fixed_count += 1
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  ✗ Failed to fix: {str(e)}"))
            else:
                # Show OK status only if verbose
                if options['verbosity'] > 1:
                    self.stdout.write(f"✓ User {user.id}: Balance OK (KES {result['actual_balance']})")
        
        # Summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('RECONCILIATION SUMMARY'))
        self.stdout.write('='*70)
        self.stdout.write(f"Total Users Checked:   {users.count()}")
        self.stdout.write(self.style.WARNING(f"Discrepancies Found:   {total_discrepancies}"))
        if fix:
            self.stdout.write(self.style.SUCCESS(f"Discrepancies Fixed:   {fixed_count}"))
        
        if total_discrepancies > 0:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  ATTENTION: Balance discrepancies detected!'
            ))
            if not fix:
                self.stdout.write('Run with --fix flag to automatically correct discrepancies')
                self.stdout.write('Review changes before doing so!\n')
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ All balances verified successfully!\n'))
