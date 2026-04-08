"""
Temporary fix views for migrating data
WARNING: These endpoints should only be used for development/migration
"""
import json
import logging
import os
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from users.models import CustomUser
from api.validators import normalize_phone_number

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def migrate_phone_numbers(request):
    """
    ONE-TIME FIX: Normalize all existing phone numbers in the database
    WARNING: This should only be run once and then the endpoint should be removed
    
    To protect this, require a secret key to be passed in the request body
    The secret key should match MIGRATION_SECRET_KEY environment variable
    
    Usage: POST to /api/auth/migrate/normalize-phones/
    Body: {"secret_key": "your-secret-key"}
    """
    try:
        data = json.loads(request.body)
        secret = data.get('secret_key')
        
        # Get secret from environment variable or use default
        MIGRATION_SECRET = os.environ.get('MIGRATION_SECRET_KEY', 'CHANGE_ME_BEFORE_PRODUCTION')
        
        if secret != MIGRATION_SECRET:
            logger.warning("Unauthorized phone number migration attempt with key: " + str(secret)[:5])
            return JsonResponse({'error': 'Unauthorized - invalid secret key'}, status=401)
        
        users = CustomUser.objects.filter(phone_number__isnull=False)
        updated_count = 0
        failed_list = []
        updated_list = []
        
        for user in users:
            original_phone = user.phone_number
            try:
                normalized_phone = normalize_phone_number(original_phone)
                if original_phone != normalized_phone:
                    user.phone_number = normalized_phone
                    user.save()
                    updated_count += 1
                    updated_list.append({'from': original_phone, 'to': normalized_phone})
                    logger.info(f'Normalized: {original_phone} → {normalized_phone}')
            except Exception as e:
                failed_list.append({'phone': original_phone, 'error': str(e)})
                logger.error(f'Failed to normalize {original_phone}: {str(e)}')
        
        return JsonResponse({
            'message': 'Phone number migration complete',
            'updated': updated_count,
            'total_users': users.count(),
            'updated_users': updated_list[:10],  # Show first 10
            'failed': failed_list
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Migration error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
