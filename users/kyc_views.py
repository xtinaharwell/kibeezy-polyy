import json
import logging
import re
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from .models import CustomUser

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



@csrf_exempt
@require_http_methods(["POST"])
def start_kyc_verification(request):
    """Start KYC verification process with OTP"""
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        phone_number = data.get('phone_number', user.phone_number)
        
        # Validate phone number
        if not _validate_phone_number(phone_number):
            return JsonResponse({'error': 'Invalid phone number format'}, status=400)
        
        # Check if phone is already verified with another account
        if CustomUser.objects.filter(phone_number=phone_number).exclude(id=user.id).exists():
            return JsonResponse({'error': 'Phone number already verified with another account'}, status=400)
        
        # Generate OTP
        otp = _generate_otp()
        
        # Store OTP in cache (expires in 10 minutes)
        cache_key = f"kyc_otp_{user.id}"
        cache.set(cache_key, otp, 600)
        
        # Store pending phone number
        cache_key_phone = f"kyc_phone_{user.id}"
        cache.set(cache_key_phone, phone_number, 600)
        
        # Log attempt
        logger.info(f"KYC OTP generation for user {user.id}, phone: {phone_number}")
        
        # In production, send real SMS
        # For now, return OTP for testing
        is_production = not _is_development()
        
        response_data = {
            'message': 'OTP sent to your phone number',
            'expires_in': 600
        }
        
        # For testing/development, include OTP
        if not is_production:
            response_data['otp_test_only'] = otp
            logger.warning(f"OTP for testing: {otp}")
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"KYC OTP generation error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_kyc_otp(request):
    """Verify KYC OTP and complete verification"""
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        otp = str(data.get('otp', '')).strip()
        
        if not otp or len(otp) != 6:
            return JsonResponse({'error': 'OTP must be 6 digits'}, status=400)
        
        # Get cached OTP
        cache_key = f"kyc_otp_{user.id}"
        stored_otp = cache.get(cache_key)
        
        if not stored_otp:
            return JsonResponse({'error': 'OTP expired or not requested'}, status=400)
        
        if otp != stored_otp:
            # Increment failed attempts
            attempts_key = f"kyc_otp_attempts_{user.id}"
            attempts = cache.get(attempts_key, 0)
            
            if attempts >= 3:
                # Lock out after 3 failed attempts
                cache.delete(cache_key)
                cache.delete(f"kyc_phone_{user.id}")
                return JsonResponse({
                    'error': 'Too many failed attempts. Please request a new OTP.'
                }, status=429)
            
            cache.set(attempts_key, attempts + 1, 600)
            return JsonResponse({'error': 'Invalid OTP'}, status=400)
        
        # OTP is correct, mark as verified
        phone_number = cache.get(f"kyc_phone_{user.id}")
        
        user.phone_number = phone_number
        user.kyc_verified = True
        user.kyc_verified_at = timezone.now()
        user.save()
        
        # Clean up cache
        cache.delete(cache_key)
        cache.delete(f"kyc_phone_{user.id}")
        cache.delete(f"kyc_otp_attempts_{user.id}")
        
        logger.info(f"KYC verified for user {user.id}, phone: {phone_number}")
        
        return JsonResponse({
            'message': 'Phone number verified successfully',
            'kyc_verified': True,
            'user': {
                'id': request.user.id,
                'phone_number': request.user.phone_number,
                'kyc_verified': request.user.kyc_verified
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"KYC OTP verification error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_kyc_status(request):
    """Get current KYC verification status"""
    if not request.user or not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    return JsonResponse({
        'kyc_verified': request.user.kyc_verified,
        'phone_number': request.user.phone_number if request.user.kyc_verified else '***',
        'verified_at': request.user.kyc_verified_at.isoformat() if request.user.kyc_verified_at else None,
        'can_trade': request.user.kyc_verified,
        'can_deposit': request.user.kyc_verified
    })


def _validate_phone_number(phone_number):
    """Validate Kenyan phone number"""
    phone_number = str(phone_number).replace('+', '').replace(' ', '').replace('-', '')
    
    # Must be 254 followed by 9 digits or 0 followed by 9 digits
    if re.match(r'^254[0-9]{9}$', phone_number) or re.match(r'^0[0-9]{9}$', phone_number):
        return True
    
    return False


def _generate_otp():
    """Generate 6-digit OTP"""
    import random
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


def _is_development():
    """Check if running in development"""
    import os
    return os.environ.get('DEBUG', 'True') == 'True'
