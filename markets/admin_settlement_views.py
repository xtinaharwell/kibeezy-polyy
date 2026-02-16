"""
Admin views for market settlement and payout management
Accessible only to staff/admin users
"""
import logging
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from markets.models import Market, Bet
from payments.models import Transaction
from payments.settlement_tasks import settle_market, send_b2c_payout, retry_failed_payouts

logger = logging.getLogger(__name__)


def is_staff(user):
    """Check if user is staff/admin"""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_staff)
@require_http_methods(["POST"])
def resolve_market(request, market_id):
    """
    Admin endpoint to manually resolve a market outcome
    
    POST /api/markets/admin/resolve/ with:
    {
        "market_id": 123,
        "outcome": "Yes"  # or "No"
    }
    
    Returns:
        {
            "status": "resolved",
            "market_id": 123,
            "outcome": "Yes",
            "settlement_task_id": "celery-task-id"
        }
    """
    try:
        market = Market.objects.get(id=market_id)
        
        if market.status == 'RESOLVED':
            return JsonResponse({
                'error': 'Market already resolved',
                'current_outcome': market.resolved_outcome
            }, status=400)
        
        data = json.loads(request.body)
        outcome = data.get('outcome')
        
        if outcome not in ['Yes', 'No']:
            return JsonResponse({'error': 'Outcome must be Yes or No'}, status=400)
        
        # Update market
        with transaction.atomic():
            market.resolved_outcome = outcome
            market.status = 'CLOSED'
            market.save()
        
        logger.info(f"Admin {request.user.phone_number} resolved market {market_id} to {outcome}")
        
        # Enqueue settlement task
        task = settle_market.delay(market_id)
        
        return JsonResponse({
            'status': 'resolved',
            'market_id': market_id,
            'outcome': outcome,
            'settlement_task_id': task.id
        })
    
    except Market.DoesNotExist:
        return JsonResponse({'error': 'Market not found'}, status=404)
    except Exception as e:
        logger.error(f"Market resolution error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff)
@require_http_methods(["GET"])
def settlement_status(request, market_id):
    """
    Check settlement status of a market
    
    GET /api/markets/admin/settlement-status/{market_id}/
    
    Returns:
        {
            "market_id": 123,
            "status": "resolved",
            "outcome": "Yes",
            "total_payouts": 150000,
            "completed_payouts": 120000,
            "failed_payouts": 30000,
            "payout_count": {
                "pending": 2,
                "completed": 18,
                "failed": 5
            }
        }
    """
    try:
        market = Market.objects.get(id=market_id)
        
        # Get payout transactions
        payouts = Transaction.objects.filter(
            related_bet__market=market,
            type='PAYOUT'
        )
        
        completed = payouts.filter(status='COMPLETED')
        failed = payouts.filter(status='FAILED')
        pending = payouts.filter(status='PENDING')
        
        completed_amount = sum(p.amount for p in completed)
        failed_amount = sum(p.amount for p in failed)
        pending_amount = sum(p.amount for p in pending)
        
        return JsonResponse({
            'market_id': market_id,
            'status': market.status,
            'outcome': market.resolved_outcome,
            'resolved_at': market.resolved_at.isoformat() if market.resolved_at else None,
            'total_payouts': str(completed_amount + failed_amount + pending_amount),
            'completed_payouts': str(completed_amount),
            'failed_payouts': str(failed_amount),
            'pending_payouts': str(pending_amount),
            'payout_count': {
                'pending': pending.count(),
                'completed': completed.count(),
                'failed': failed.count()
            }
        })
    
    except Market.DoesNotExist:
        return JsonResponse({'error': 'Market not found'}, status=404)


@login_required
@user_passes_test(is_staff)
@require_http_methods(["POST"])
def retry_payout(request):
    """
    Manually retry a failed payout transaction
    
    POST /api/payments/admin/retry-payout/ with:
    {
        "transaction_id": 456
    }
    
    Returns:
        {
            "status": "retried",
            "transaction_id": 456,
            "new_status": "PENDING"
        }
    """
    try:
        data = json.loads(request.body)
        transaction_id = data.get('transaction_id')
        
        tx = Transaction.objects.get(id=transaction_id, type='PAYOUT')
        
        # Reset status to PENDING
        tx.status = 'PENDING'
        tx.save()
        
        # Re-enqueue B2C call
        send_b2c_payout.delay(transaction_id)
        
        logger.info(f"Admin {request.user.phone_number} retried payout transaction {transaction_id}")
        
        return JsonResponse({
            'status': 'retried',
            'transaction_id': transaction_id,
            'new_status': 'PENDING'
        })
    
    except Transaction.DoesNotExist:
        return JsonResponse({'error': 'Transaction not found or wrong type'}, status=404)
    except Exception as e:
        logger.error(f"Payout retry error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff)
@require_http_methods(["POST"])
def retry_failed_payouts_batch(request):
    """
    Admin batch retry of all failed payouts in past N hours
    
    POST /api/payments/admin/retry-failed-payouts/ with:
    {
        "hours": 24  # optional, default 24
    }
    
    Returns:
        {
            "status": "retried",
            "count": 5
        }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        hours = data.get('hours', 24)
        
        # Enqueue batch retry task
        task = retry_failed_payouts.delay(hours)
        
        logger.info(f"Admin {request.user.phone_number} triggered batch retry for payouts from past {hours}h")
        
        return JsonResponse({
            'status': 'batch_retry_queued',
            'task_id': task.id,
            'hours': hours
        })
    
    except Exception as e:
        logger.error(f"Batch retry error: {e}")
        return JsonResponse({'error': str(e)}, status=500)
