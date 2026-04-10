"""
Audit Daily Report Command

Generate comprehensive audit reports for compliance.

Usage:
    python manage.py audit_report --date today
    python manage.py audit_report --date 2026-04-10
    python manage.py audit_report --email admin@cache.co.ke
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from audit.models import AuditLog, AuditAlert, AuditSummary
from payments.models import Transaction
from users.models import CustomUser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate comprehensive audit report'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            default='today',
            help='Date for report (today, yesterday, YYYY-MM-DD)'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email address to send report to'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='File path to save report (e.g., /tmp/report.txt)'
        )

    def handle(self, *args, **options):
        date_param = options['date']
        email = options['email']
        output_file = options['output']
        
        # Parse date
        if date_param == 'today':
            target_date = timezone.now().date()
        elif date_param == 'yesterday':
            target_date = (timezone.now() - timedelta(days=1)).date()
        else:
            try:
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                raise CommandError(f'Invalid date: {date_param}')
        
        # Generate report
        report = self.generate_report(target_date)
        
        # Output
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            self.stdout.write(self.style.SUCCESS(f'Report saved to {output_file}'))
        else:
            self.stdout.write(report)
        
        # Email
        if email:
            self.send_report_email(email, target_date, report)

    def generate_report(self, target_date):
        """Generate comprehensive audit report"""
        
        start = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
        end = timezone.make_aware(datetime.combine(target_date, datetime.max.time()))
        
        logs = AuditLog.objects.filter(created_at__gte=start, created_at__lte=end)
        alerts = AuditAlert.objects.filter(created_at__gte=start, created_at__lte=end)
        
        # Report header
        report = f"""
{'='*80}
AUDIT TRAIL REPORT
{'='*80}
Date: {target_date}
Generated: {timezone.now().isoformat()}

"""
        
        # 1. EXECUTIVE SUMMARY
        report += f"""
{'-'*80}
1. EXECUTIVE SUMMARY
{'-'*80}

Total Actions: {logs.count()}
Critical Events: {logs.filter(severity='CRITICAL').count()}
High Priority: {logs.filter(severity='HIGH').count()}
Security Alerts: {alerts.count()}

Unique Users Acting: {logs.values('user_id').distinct().count()}
Unique Users Affected: {logs.values('object_id').filter(content_type='users.CustomUser').distinct().count()}

"""
        
        # 2. ACTION BREAKDOWN
        report += f"""
{'-'*80}
2. ACTION BREAKDOWN
{'-'*80}

"""
        
        action_counts = logs.values('action').annotate(count=Count('id')).order_by('-count')
        for action_stat in action_counts:
            report += f"  {action_stat['action']}: {action_stat['count']}\n"
        
        # 3. FINANCIAL ACTIVITY
        report += f"""

{'-'*80}
3. FINANCIAL ACTIVITY
{'-'*80}

"""
        
        deposits = logs.filter(action='DEPOSIT')
        withdrawals = logs.filter(action='WITHDRAWAL')
        payouts = logs.filter(action='PAYOUT_ISSUED')
        
        report += f"  Deposits: {deposits.count()}\n"
        report += f"  Withdrawals: {withdrawals.count()}\n"
        report += f"  Payouts: {payouts.count()}\n"
        
        # Total amounts
        txns = Transaction.objects.filter(
            created_at__gte=start,
            created_at__lte=end,
            status='COMPLETED'
        )
        total_deposited = txns.filter(type='DEPOSIT').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        total_withdrawn = txns.filter(type='WITHDRAWAL').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        report += f"\n  Total Deposited: KES {total_deposited:,.2f}\n"
        report += f"  Total Withdrawn: KES {total_withdrawn:,.2f}\n"
        report += f"  Net Flow: KES {(total_deposited - total_withdrawn):,.2f}\n"
        
        # 4. USER BALANCE CHANGES
        report += f"""

{'-'*80}
4. USER BALANCE ADJUSTMENTS (Top 20)
{'-'*80}

"""
        
        balance_changes = logs.filter(action='BALANCE_ADJUSTED').order_by('-created_at')[:20]
        if balance_changes:
            report += f"{'Timestamp':<20} {'User':<15} {'Amount':<15} {'Description':<30}\n"
            report += "-" * 80 + "\n"
            
            for log in balance_changes:
                amount = log.changes.get('balance', {}).get('delta', 'N/A')
                user_phone = log.changes.get('user', {}).get('phone', 'Unknown')
                timestamp = log.created_at.strftime('%Y-%m-%d %H:%M:%S')
                
                report += f"{timestamp:<20} {user_phone:<15} {str(amount):<15} {log.description[:30]:<30}\n"
        else:
            report += "  No balance adjustments recorded\n"
        
        # 5. CRITICAL EVENTS
        report += f"""

{'-'*80}
5. CRITICAL EVENTS
{'-'*80}

"""
        
        critical_logs = logs.filter(severity='CRITICAL').order_by('-created_at')
        if critical_logs:
            for log in critical_logs[:10]:
                report += f"\n  [{log.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {log.action}\n"
                report += f"    Object: {log.object_repr[:60]}\n"
                report += f"    User: {log.user.phone_number if log.user else 'System'}\n"
                report += f"    Description: {log.description}\n"
        else:
            report += "  ✅ No critical events\n"
        
        # 6. SECURITY ALERTS
        report += f"""

{'-'*80}
6. SECURITY ALERTS
{'-'*80}

"""
        
        if alerts.exists():
            report += f"Total Alerts: {alerts.count()}\n"
            report += f"Acknowledged: {alerts.filter(acknowledged=True).count()}\n"
            report += f"Pending: {alerts.filter(acknowledged=False).count()}\n"
            
            report += f"\nAlert Details:\n"
            for alert in alerts.order_by('-created_at')[:10]:
                status = "✅ Acknowledged" if alert.acknowledged else "⏳ Pending"
                report += f"\n  [{status}] {alert.alert_type} ({alert.severity})\n"
                report += f"    {alert.description}\n"
        else:
            report += "  ✅ No security alerts\n"
        
        # 7. HASH INTEGRITY CHECK
        report += f"""

{'-'*80}
7. INTEGRITY VERIFICATION
{'-'*80}

"""
        
        verified = sum(1 for log in logs if log.verify_hash())
        report += f"  Records Verified: {verified}/{logs.count()}\n"
        
        if verified < logs.count():
            corrupted = logs.exclude(id__in=[log.id for log in logs if log.verify_hash()])
            report += f"  ⚠️  CORRUPTION DETECTED: {corrupted.count()} records failed verification\n"
            for log in corrupted[:5]:
                report += f"    - {log.id}: {log.action}\n"
        else:
            report += f"  ✅ All records verified\n"
        
        # 8. TOP USERS
        report += f"""

{'-'*80}
8. MOST ACTIVE USERS (Top 10)
{'-'*80}

"""
        
        top_users = logs.filter(user__isnull=False).values('user__phone_number').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        for user_stat in top_users:
            report += f"  {user_stat['user__phone_number']}: {user_stat['count']} actions\n"
        
        # Footer
        report += f"""

{'-'*80}
END OF REPORT
{'-'*80}

Report generated automatically by CACHE Audit System
For questions or concerns, contact: compliance@cache.co.ke
"""
        
        return report
    
    def send_report_email(self, recipient_email, target_date, report):
        """Send report via email"""
        
        subject = f"CACHE Audit Report - {target_date}"
        
        try:
            send_mail(
                subject=subject,
                message=report,
                from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@cache.co.ke',
                recipient_list=[recipient_email],
                fail_silently=False,
            )
            logger.info(f"✓ Report sent to {recipient_email}")
            self.stdout.write(self.style.SUCCESS(f"✓ Report sent to {recipient_email}"))
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Failed to send email: {str(e)}"))
