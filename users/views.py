import json
import logging
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_http_methods
from django.middleware.csrf import get_token
from .models import CustomUser
from api.validators import validate_phone_number, validate_pin, validate_full_name, ValidationError

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def signup_view(request):
    try:
        data = json.loads(request.body)
        full_name = data.get('full_name')
        phone_number = data.get('phone_number')
        pin = data.get('pin')

        if not all([full_name, phone_number, pin]):
            return JsonResponse({'error': 'Missing required fields: full_name, phone_number, pin'}, status=400)
        
        # Validate inputs
        try:
            full_name = validate_full_name(full_name)
            phone_number = validate_phone_number(phone_number)
            pin = validate_pin(pin)
        except ValidationError as e:
            return JsonResponse({'error': e.message}, status=400)

        if CustomUser.objects.filter(phone_number=phone_number).exists():
            return JsonResponse({'error': 'Phone number already registered'}, status=400)

        user = CustomUser.objects.create_user(
            phone_number=phone_number,
            full_name=full_name,
            pin=pin
        )
        logger.info(f"New user created: {phone_number}")
        return JsonResponse({
            'message': 'Account created successfully', 
            'user': {
                'phone_number': user.phone_number, 
                'full_name': user.full_name,
                'id': user.id
            }
        }, status=201)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ValidationError as e:
        return JsonResponse({'error': e.message}, status=400)
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@ensure_csrf_cookie
@require_http_methods(["POST"])
def login_view(request):
    try:
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        pin = data.get('pin')

        if not all([phone_number, pin]):
            return JsonResponse({'error': 'Missing credentials: phone_number, pin'}, status=400)

        logger.info(f"Login attempt for phone: {phone_number}")
        user = authenticate(request, phone_number=phone_number, password=pin)
        if user is not None:
            logger.info(f"User authenticated: {user.phone_number}, User ID: {user.id}")
            login(request, user)  # This sets the session cookie
            # Force session save to database
            request.session.save()
            logger.info(f"Session key after login: {request.session.session_key}")
            # Get CSRF token
            csrf_token = get_token(request)
            
            response = JsonResponse({
                'message': 'Login successful', 
                'user': {
                    'phone_number': user.phone_number, 
                    'full_name': user.full_name,
                    'id': user.id,
                    'kyc_verified': user.kyc_verified
                },
                'csrf_token': csrf_token
            })
            logger.info(f"Login successful for {phone_number}, setting cookies")
            logger.info(f"Response headers: {response}")
            return response
        else:
            logger.warning(f"Failed authentication for phone: {phone_number}")
            return JsonResponse({'error': 'Invalid phone number or PIN'}, status=401)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def check_auth(request):
    """Check if user is authenticated"""
    logger.info(f"Checking auth - User: {request.user}, Authenticated: {request.user.is_authenticated if request.user else 'None'}")
    logger.info(f"Session key: {request.session.session_key}")
    
    if request.user and request.user.is_authenticated:
        logger.info(f"Auth check successful for {request.user.phone_number}")
        return JsonResponse({
            'authenticated': True,
            'user': {
                'phone_number': request.user.phone_number,
                'full_name': request.user.full_name,
                'id': request.user.id,
                'balance': str(request.user.balance),
                'kyc_verified': request.user.kyc_verified
            }
        })
    else:
        logger.warning(f"Auth check failed - user not authenticated")
        return JsonResponse({
            'authenticated': False,
            'error': 'Not authenticated'
        }, status=401)


@csrf_exempt
@require_http_methods(["POST"])
def logout_view(request):
    """Logout user"""
    logout(request)
    logger.info(f"User logged out")
    return JsonResponse({'message': 'Logged out successfully'})
