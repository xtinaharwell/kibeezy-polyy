"""
Audit Trail Views & API Endpoints

Provides access to audit logs with filtering and reporting.
"""

import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.shortcuts import get_object_or_404

from audit.models import AuditLog, AuditAlert, AccessLog, AuditSummary
from users.models import CustomUser

logger = logging.getLogger(__name__)


def is_admin_or_staff(user):
    """Check if user is admin or finance staff"""
    return user.is_staff or user.is_superuser


@login_required
@require_http_methods(["GET"])
def view_audit_logs(request):
    """
    View audit logs with filtering.
    
    Query parameters:
    - action: Filter by action type
    - object_type: Filter by model (e.g., 'payments.Transaction')
    - user_id: Filter by user who made change
    - severity: Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)
    - user_phone_or_id: Filter by affected user's phone or ID
    - start_date: Filter from date (YYYY-MM-DD)
    - end_date: Filter to date (YYYY-MM-DD)
    - limit: Number of records (default 100, max 1000)
    - offset: Pagination offset
    """
    
    if not is_admin_or_staff(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Start with all logs
    logs = AuditLog.objects.all()
    
    # Apply filters
    action = request.GET.get('action')
    if action:
        logs = logs.filter(action=action)
    
    object_type = request.GET.get('object_type')
    if object_type:
        logs = logs.filter(content_type=object_type)
    
    user_id = request.GET.get('user_id')
    if user_id:
        logs = logs.filter(user_id=user_id)
    
    severity = request.GET.get('severity')
    if severity:
        logs = logs.filter(severity=severity)
    
    # Filter by affected user (e.g., user whose balance was changed)
    user_phone = request.GET.get('user_phone_or_id')
    if user_phone:
        # Try to find user
        try:
            affected_user = CustomUser.objects.get(
                Q(phone_number=user_phone) | Q(id=user_phone)
            )
            logs = logs.filter(object_id=str(affected_user.id), content_type='users.CustomUser')
        except CustomUser.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
    
    # Date range filtering
    start_date = request.GET.get('start_date')
    if start_date:
        logs = logs.filter(created_at__gte=start_date)
    
    end_date = request.GET.get('end_date')
    if end_date:
        logs = logs.filter(created_at__lte=end_date)
    
    # Pagination
    limit = min(int(request.GET.get('limit', 100)), 1000)
    offset = int(request.GET.get('offset', 0))
    
    total = logs.count()
    logs = logs[offset:offset + limit]
    
    # Serialize response
    data = []
    for log in logs:
        data.append({
            'id': log.id,
            'action': log.action,
            'severity': log.severity,
            'object_type': log.content_type,
            'object_id': log.object_id,
            'object_repr': log.object_repr,
            'user': {'id': log.user.id, 'phone': log.user.phone_number} if log.user else None,
            'ip_address': log.ip_address,
            'changes': log.changes,
            'before_values': log.before_values,
            'after_values': log.after_values,
            'created_at': log.created_at.isoformat(),
            'hash_verified': log.hash_verified,
            'description': log.description,
        })
    
    return JsonResponse({
        'total': total,
        'limit': limit,
        'offset': offset,
        'logs': data
    })


@login_required
@require_http_methods(["GET"])
def audit_log_detail(request, log_id):
    """Get detailed information about a specific audit log"""
    
    if not is_admin_or_staff(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    log = get_object_or_404(AuditLog, id=log_id)
    
    # Verify hash integrity
    hash_verified = log.verify_hash()
    
    return JsonResponse({
        'id': log.id,
        'action': log.action,
        'severity': log.severity,
        'object_type': log.content_type,
        'object_id': log.object_id,
        'object_repr': log.object_repr,
        'user': {'id': log.user.id, 'phone': log.user.phone_number} if log.user else None,
        'ip_address': log.ip_address,
        'user_agent': log.user_agent,
        'changes': log.changes,
        'before_values': log.before_values,
        'after_values': log.after_values,
        'description': log.description,
        'created_at': log.created_at.isoformat(),
        'current_hash': log.current_hash,
        'previous_hash': log.previous_hash,
        'hash_verified': hash_verified,
        'warning': None if hash_verified else '⚠️ HASH VERIFICATION FAILED - RECORD MAY BE TAMPERED WITH'
    })


@login_required
@require_http_methods(["GET"])
def audit_summary(request):
    """
    Get audit summary (daily report)
    
    Query parameters:
    - date: Specific date (YYYY-MM-DD) or 'today', 'yesterday', 'last_7_days', 'last_30_days'
    """
    
    if not is_admin_or_staff(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    date_param = request.GET.get('date', 'today')
    
    # Parse date parameter
    if date_param == 'today':
        target_date = timezone.now().date()
    elif date_param == 'yesterday':
        target_date = (timezone.now() - timedelta(days=1)).date()
    else:
        try:
            target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format (use YYYY-MM-DD)'}, status=400)
    
    # Get or create summary
    summary, _ = AuditSummary.objects.get_or_create(date=target_date)
    
    # Calculate stats if empty
    if summary.total_actions == 0:
        start = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
        end = timezone.make_aware(datetime.combine(target_date, datetime.max.time()))
        
        logs = AuditLog.objects.filter(created_at__gte=start, created_at__lte=end)
        
        summary.total_actions = logs.count()
        summary.creates = logs.filter(action='CREATE').count()
        summary.updates = logs.filter(action='UPDATE').count()
        summary.deletes = logs.filter(action='DELETE').count()
        summary.financial_actions = logs.filter(
            action__in=['DEPOSIT', 'WITHDRAWAL', 'PAYOUT_ISSUED']
        ).count()
        summary.admin_actions = logs.filter(action='ADMIN_ACTION').count()
        summary.critical_count = logs.filter(severity='CRITICAL').count()
        summary.high_count = logs.filter(severity='HIGH').count()
        summary.unique_users = logs.values('user_id').distinct().count()
        
        # Calculate total financial amount
        from payments.models import Transaction
        transactions = Transaction.objects.filter(
            created_at__gte=start,
            created_at__lte=end,
            status='COMPLETED',
            type__in=['DEPOSIT', 'WITHDRAWAL']
        )
        summary.total_amount_processed = transactions.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        summary.save()
    
    return JsonResponse({
        'date': str(target_date),
        'total_actions': summary.total_actions,
        'breakdown': {
            'creates': summary.creates,
            'updates': summary.updates,
            'deletes': summary.deletes,
            'financial': summary.financial_actions,
            'admin': summary.admin_actions,
        },
        'risk_indicators': {
            'critical': summary.critical_count,
            'high': summary.high_count,
        },
        'unique_users': summary.unique_users,
        'total_amount_processed': str(summary.total_amount_processed),
    })


@login_required
@require_http_methods(["GET"])
def audit_alerts(request):
    """
    View security alerts generated from audit patterns
    
    Query parameters:
    - resolved: Filter by resolved status (true/false)
    - severity: Filter by severity
    - limit: Number of records
    """
    
    if not is_admin_or_staff(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    alerts = AuditAlert.objects.all()
    
    # Filter by resolution status
    resolved = request.GET.get('resolved')
    if resolved is not None:
        alerts = alerts.filter(resolved=resolved.lower() == 'true')
    
    # Filter by severity
    severity = request.GET.get('severity')
    if severity:
        alerts = alerts.filter(severity=severity)
    
    # Pagination
    limit = min(int(request.GET.get('limit', 50)), 500)
    offset = int(request.GET.get('offset', 0))
    
    total = alerts.count()
    alerts = alerts[offset:offset + limit]
    
    data = []
    for alert in alerts:
        data.append({
            'id': alert.id,
            'type': alert.alert_type,
            'severity': alert.severity,
            'description': alert.description,
            'user': {'id': alert.user.id, 'phone': alert.user.phone_number} if alert.user else None,
            'acknowledged': alert.acknowledged,
            'resolved': alert.resolved,
            'created_at': alert.created_at.isoformat(),
        })
    
    return JsonResponse({
        'total': total,
        'limit': limit,
        'offset': offset,
        'alerts': data
    })


@login_required
@require_http_methods(["POST"])
def acknowledge_alert(request, alert_id):
    """Mark an audit alert as acknowledged"""
    
    if not is_admin_or_staff(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    alert = get_object_or_404(AuditAlert, id=alert_id)
    
    try:
        data = json.loads(request.body)
        notes = data.get('notes', '')
    except:
        notes = ''
    
    alert.acknowledge(request.user, notes)
    
    return JsonResponse({
        'id': alert.id,
        'acknowledged': True,
        'acknowledged_by': request.user.phone_number,
        'acknowledged_at': alert.acknowledged_at.isoformat()
    })


@login_required
@require_http_methods(["GET"])
def verify_audit_chain(request):
    """
    Verify the integrity of the audit log chain.
    Checks that all hashes are valid and unbroken.
    
    Returns the first point of corruption (if any) or all-clear.
    """
    
    if not is_admin_or_staff(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    logs = AuditLog.objects.all().order_by('created_at')
    
    corrupted = []
    verified_count = 0
    
    for log in logs:
        if not log.verify_hash():
            corrupted.append({
                'id': log.id,
                'action': log.action,
                'created_at': log.created_at.isoformat(),
                'issue': 'Hash verification failed'
            })
        else:
            verified_count += 1
    
    if corrupted:
        logger.critical(f"⚠️  AUDIT CHAIN CORRUPTION DETECTED: {len(corrupted)} records")
    else:
        logger.info(f"✓ Audit chain verified: {verified_count} records")
    
    return JsonResponse({
        'status': 'OK' if not corrupted else 'CORRUPTED',
        'verified_count': verified_count,
        'corrupted_count': len(corrupted),
        'corrupted_records': corrupted[:10],  # Show first 10
        'warning': None if not corrupted else '⚠️  CRITICAL: Audit log corruption detected!'
    })


@login_required
@require_http_methods(["GET"])
def user_activity_report(request, user_phone):
    """
    Get detailed activity report for a specific user
    (what they did, what was done to them)
    """
    
    if not is_admin_or_staff(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        user = CustomUser.objects.get(phone_number=user_phone)
    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    # What this user did
    actions_by_user = AuditLog.objects.filter(user=user).values('action').annotate(count=Count('id'))
    
    # What was done to this user
    changes_to_user = AuditLog.objects.filter(
        object_id=str(user.id),
        content_type='users.CustomUser'
    )
    
    # Balance changes
    balance_changes = changes_to_user.filter(action='BALANCE_ADJUSTED')
    
    return JsonResponse({
        'user': {
            'id': user.id,
            'phone': user.phone_number,
            'kyc_verified': user.kyc_verified,
            'current_balance': str(user.balance),
        },
        'actions_performed': list(actions_by_user),
        'changes_to_account': {
            'total_records': changes_to_user.count(),
            'balance_adjustments': balance_changes.count(),
            'recent_changes': [
                {
                    'action': log.action,
                    'changes': log.changes,
                    'created_at': log.created_at.isoformat(),
                }
                for log in changes_to_user.order_by('-created_at')[:20]
            ]
        }
    })
