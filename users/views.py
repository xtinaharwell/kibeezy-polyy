import json
import logging
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.middleware.csrf import get_token
from .models import CustomUser

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
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        if len(str(pin)) != 4 or not str(pin).isdigit():
            return JsonResponse({'error': 'PIN must be a 4-digit number'}, status=400)

        if CustomUser.objects.filter(phone_number=phone_number).exists():
            return JsonResponse({'error': 'Phone number already registered'}, status=400)

        user = CustomUser.objects.create_user(
            phone_number=phone_number,
            full_name=full_name,
            pin=pin
        )
        logger.info(f"New user created: {phone_number}")
        return JsonResponse({'message': 'Account created successfully', 'user': {'phone_number': user.phone_number, 'full_name': user.full_name}}, status=201)
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    try:
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        pin = data.get('pin')

        if not all([phone_number, pin]):
            return JsonResponse({'error': 'Missing credentials'}, status=400)

        logger.info(f"Login attempt for phone: {phone_number}")
        user = authenticate(request, phone_number=phone_number, password=pin)
        if user is not None:
            logger.info(f"User authenticated: {user.phone_number}, User ID: {user.id}")
            login(request, user)  # This sets the session cookie
            logger.info(f"Session key after login: {request.session.session_key}")
            # Get CSRF token
            csrf_token = get_token(request)
            response = JsonResponse({
                'message': 'Login successful', 
                'user': {
                    'phone_number': user.phone_number, 
                    'full_name': user.full_name,
                    'id': user.id
                },
                'csrf_token': csrf_token
            })
            logger.info(f"Login successful for {phone_number}, setting cookies")
            return response
        else:
            logger.warning(f"Failed authentication for phone: {phone_number}")
            return JsonResponse({'error': 'Invalid phone number or PIN'}, status=401)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def check_auth(request):
    """Debug endpoint to check if user is authenticated"""
    logger.info(f"Auth check - User: {request.user}, Is authenticated: {request.user.is_authenticated}")
    logger.info(f"Session key: {request.session.session_key}, Cookies received: {request.COOKIES}")
    
    if request.user and request.user.is_authenticated:
        return JsonResponse({
            'authenticated': True,
            'user': {
                'phone_number': request.user.phone_number,
                'full_name': request.user.full_name,
                'id': request.user.id
            }
        })
    else:
        return JsonResponse({
            'authenticated': False,
            'error': 'Not authenticated',
            'session_key': request.session.session_key,
            'cookies': str(request.COOKIES)
        }, status=401)
