from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from notifications.models import Notification
from users.models import CustomUser

logger = logging.getLogger(__name__)


def get_authenticated_user(request):
    """Get authenticated user from session or X-User-Phone-Number header"""
    # Try session-based auth first
    if request.user and request.user.is_authenticated:
        return request.user
    
    # Fall back to header-based auth
    phone_number = request.headers.get('X-User-Phone-Number')
    if phone_number:
        try:
            return CustomUser.objects.get(phone_number=phone_number)
        except CustomUser.DoesNotExist:
            return None
    
    return None


@require_http_methods(["GET"])
def get_notifications(request):
    """Get notifications for authenticated user"""
    try:
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        # Get unread count
        unread_count = Notification.objects.filter(user=user, is_read=False).count()
        
        # Get recent notifications (last 20)
        notifications = Notification.objects.filter(user=user).values(
            'id', 'type', 'title', 'message', 'color_class', 'is_read',
            'created_at', 'related_market_id', 'related_transaction_id', 'related_bet_id'
        )[:20]
        
        notifications_list = []
        for notif in notifications:
            created_at = notif['created_at']
            # Calculate relative time
            from django.utils import timezone
            now = timezone.now()
            diff = now - created_at
            
            if diff.days > 0:
                time_str = f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
            elif diff.seconds >= 3600:
                hours = diff.seconds // 3600
                time_str = f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif diff.seconds >= 60:
                minutes = diff.seconds // 60
                time_str = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                time_str = "Just now"
            
            notifications_list.append({
                'id': notif['id'],
                'type': notif['type'],
                'title': notif['title'],
                'message': notif['message'],
                'color_class': notif['color_class'],
                'is_read': notif['is_read'],
                'time': time_str,
                'related_market_id': notif['related_market_id'],
                'related_transaction_id': notif['related_transaction_id'],
                'related_bet_id': notif['related_bet_id'],
            })
        
        return JsonResponse({
            'notifications': notifications_list,
            'unread_count': unread_count
        })
    
    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    try:
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.is_read = True
            notification.save()
            
            return JsonResponse({'message': 'Notification marked as read'})
        except Notification.DoesNotExist:
            return JsonResponse({'error': 'Notification not found'}, status=404)
    
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def mark_all_read(request):
    """Mark all unread notifications as read"""
    try:
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        count = Notification.objects.filter(user=user, is_read=False).update(is_read=True)
        
        return JsonResponse({
            'message': f'{count} notifications marked as read'
        })
    
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


def create_notification(user, type_choice, title, message, color_class='blue', 
                       related_market_id=None, related_transaction_id=None, related_bet_id=None):
    """Helper function to create notifications"""
    try:
        notification = Notification.objects.create(
            user=user,
            type=type_choice,
            title=title,
            message=message,
            color_class=color_class,
            related_market_id=related_market_id,
            related_transaction_id=related_transaction_id,
            related_bet_id=related_bet_id,
        )
        logger.info(f"✅ Notification created for {user.phone_number}: {type_choice} - {title}")
        return notification
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}", exc_info=True)
        return None
