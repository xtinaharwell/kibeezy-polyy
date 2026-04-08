import json
import logging
from django.contrib.auth import authenticate, login, logout
from django.db.models import Sum, Q, Value, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_http_methods
from django.middleware.csrf import get_token
from .models import CustomUser
from api.validators import validate_phone_number, validate_password, validate_full_name, normalize_phone_number, ValidationError
from notifications.views import create_notification

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def signup_view(request):
    try:
        data = json.loads(request.body)
        full_name = data.get('full_name')
        phone_number = data.get('phone_number')
        password = data.get('password')

        if not all([full_name, phone_number, password]):
            return JsonResponse({'error': 'Missing required fields: full_name, phone_number, password'}, status=400)
        
        # Validate inputs
        try:
            full_name = validate_full_name(full_name)
            phone_number = validate_phone_number(phone_number)
            password = validate_password(password)
        except ValidationError as e:
            return JsonResponse({'error': e.message}, status=400)

        if CustomUser.objects.filter(phone_number=phone_number).exists():
            return JsonResponse({'error': 'Phone number already registered'}, status=400)

        user = CustomUser.objects.create_user(
            phone_number=phone_number,
            full_name=full_name,
            password=password
        )
        logger.info(f"New user created: {phone_number}")
        
        # Create welcome notification
        create_notification(
            user=user,
            type_choice='WELCOME',
            title='Welcome to CACHE!',
            message='Start predicting markets to earn rewards',
            color_class='blue'
        )
        
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
        password = data.get('password')

        if not all([phone_number, password]):
            return JsonResponse({'error': 'Missing credentials: phone_number, password'}, status=400)

        # Normalize phone number before authentication
        try:
            phone_number = normalize_phone_number(phone_number)
        except:
            return JsonResponse({'error': 'Invalid phone number format'}, status=400)

        logger.info(f"Login attempt for phone: {phone_number}")
        user = authenticate(request, phone_number=phone_number, password=password)
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
                    'kyc_verified': user.kyc_verified,
                    'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                },
                'csrf_token': csrf_token
            })
            logger.info(f"Login successful for {phone_number}, setting cookies")
            logger.info(f"Response headers: {response}")
            return response
        else:
            logger.warning(f"Failed authentication for phone: {phone_number}")
            return JsonResponse({'error': 'Invalid phone number or password'}, status=401)
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
                'kyc_verified': request.user.kyc_verified,
                'date_joined': request.user.date_joined.isoformat() if request.user.date_joined else None,
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


@csrf_exempt
@require_http_methods(["POST"])
def update_profile_view(request):
    """Update user profile information"""
    # Try session-based auth first
    user = request.user if request.user and request.user.is_authenticated else None
    
    # Fall back to header-based auth
    if not user:
        phone_number = request.headers.get('X-User-Phone-Number')
        if phone_number:
            try:
                # Normalize phone number
                phone_number = normalize_phone_number(phone_number)
                user = CustomUser.objects.get(phone_number=phone_number)
            except CustomUser.DoesNotExist:
                user = None
    
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        full_name = data.get('full_name')
        
        if full_name:
            try:
                full_name = validate_full_name(full_name)
                user.full_name = full_name
                user.save()
            except ValidationError as e:
                return JsonResponse({'error': e.message}, status=400)
        
        logger.info(f"Profile updated for user: {user.phone_number}")
        return JsonResponse({
            'message': 'Profile updated successfully',
            'user': {
                'phone_number': user.phone_number,
                'full_name': user.full_name,
                'balance': str(user.balance),
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def leaderboard_view(request):
    """Return the top payout winners by total completed payout amount and top wins."""
    try:
        top_winners = (
            CustomUser.objects
                .annotate(total_winnings=Coalesce(
                    Sum('transactions__amount', filter=Q(transactions__type='PAYOUT', transactions__status='COMPLETED')),
                    Value(0, output_field=DecimalField())
                ))
                .filter(total_winnings__gt=0)
                .order_by('-total_winnings')[:10]
        )

        leaderboard_data = [
            {
                'id': user.id,
                'full_name': user.full_name,
                'phone_number': user.phone_number,
                'balance': str(user.balance),
                'total_winnings': str(user.total_winnings),
            }
            for user in top_winners
        ]

        # Get top wins from bets
        from markets.models import Bet, Market
        top_wins_list = Bet.objects.filter(
            result='WON',
            payout__isnull=False
        ).select_related('user', 'market').order_by('-payout')[:6]

        top_wins_data = [
            {
                'id': bet.id,
                'user_name': bet.user.full_name[:20] if bet.user.full_name else bet.user.phone_number,
                'market_title': bet.market.question[:50],
                'profit': int(float(bet.payout or 0) - float(bet.amount)),
                'avatar_color': f'bg-{["blue", "green", "purple", "orange", "pink", "cyan"][i % 6]}-500',
            }
            for i, bet in enumerate(top_wins_list)
        ]

        return JsonResponse({'leaderboard': leaderboard_data, 'top_wins': top_wins_data})
    except Exception as e:
        logger.error(f"Leaderboard error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def admin_list_users(request):
    """List all users with their support staff status (admin only)"""
    try:
        # Check if user is admin (via session or phone header)
        is_admin = False
        
        # Check Django authenticated user (for direct Django requests)
        if request.user.is_authenticated and request.user.is_staff:
            is_admin = True
        # Check phone header (for API requests from frontend)
        elif request.headers.get('X-User-Phone-Number'):
            phone_number = request.headers.get('X-User-Phone-Number')
            try:
                # Normalize phone number
                phone_number = normalize_phone_number(phone_number)
                user_obj = CustomUser.objects.get(phone_number=phone_number)
                if user_obj.is_staff or user_obj.is_superuser:
                    is_admin = True
            except CustomUser.DoesNotExist:
                pass
        
        if not is_admin:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        users = CustomUser.objects.values(
            'id', 'full_name', 'phone_number', 'balance', 'is_support_staff', 
            'kyc_verified', 'is_active', 'date_joined'
        ).order_by('-date_joined')
        
        return JsonResponse({
            'users': list(users),
            'count': users.count()
        }, status=200)
    except Exception as e:
        logger.error(f"Admin list users error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PATCH"])
def admin_toggle_support_staff(request, user_id):
    """Toggle support staff status for a user (admin only)"""
    try:
        # Check if user is admin (via session or phone header)
        is_admin = False
        
        # Check Django authenticated user
        if request.user.is_authenticated and request.user.is_staff:
            is_admin = True
        # Check phone header
        elif request.headers.get('X-User-Phone-Number'):
            phone_number = request.headers.get('X-User-Phone-Number')
            try:
                user_obj = CustomUser.objects.get(phone_number=phone_number)
                if user_obj.is_staff or user_obj.is_superuser:
                    is_admin = True
            except CustomUser.DoesNotExist:
                pass
        
        if not is_admin:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        # Get the target user
        try:
            target_user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        
        # Parse request body
        data = json.loads(request.body)
        is_support_staff = data.get('is_support_staff')
        
        if is_support_staff is None:
            return JsonResponse({'error': 'is_support_staff field required'}, status=400)
        
        # Update support staff status
        target_user.is_support_staff = bool(is_support_staff)
        target_user.save()
        
        logger.info(f"User {user_id} support staff status changed to {target_user.is_support_staff}")
        
        return JsonResponse({
            'id': target_user.id,
            'full_name': target_user.full_name,
            'phone_number': target_user.phone_number,
            'is_support_staff': target_user.is_support_staff,
            'message': f"Support staff status updated successfully"
        }, status=200)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Admin toggle support staff error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def google_auth_view(request):
    """
    Google OAuth authentication endpoint.
    Creates or retrieves a user from Google OAuth data.
    
    Expected JSON body:
    {
        "email": "user@example.com",
        "name": "User Name",
        "google_id": "google-user-id",
        "picture": "https://profile-picture-url"
    }
    """
    try:
        data = json.loads(request.body)
        email = data.get('email')
        name = data.get('name')
        google_id = data.get('google_id')
        picture = data.get('picture')
        
        if not all([email, name, google_id]):
            return JsonResponse({
                'error': 'Missing required fields: email, name, google_id'
            }, status=400)
        
        # Try to get existing user by google_id
        user = CustomUser.objects.filter(google_id=google_id).first()
        
        if not user:
            # Try to get existing user by email
            user = CustomUser.objects.filter(email=email).first()
        
        if not user:
            # Create new user with Google data
            user = CustomUser.objects.create_user(
                phone_number=None,  # Not required for Google users
                full_name=name,
                password=None,  # No password for Google OAuth users
                email=email,
                google_id=google_id,
                picture=picture
            )
            logger.info(f"New Google user created: {email} (Google ID: {google_id})")
            
            # Create welcome notification
            create_notification(
                user=user,
                type_choice='WELCOME',
                title='Welcome to CACHE!',
                message='Start predicting markets to earn rewards',
                color_class='blue'
            )
        else:
            # Update existing user with Google data if needed
            user.google_id = google_id
            user.picture = picture
            if not user.email:
                user.email = email
            user.save()
            logger.info(f"Existing user linked to Google: {email}")
        
        # Create Django session for the Google user (same as phone login)
        # This ensures backend endpoints can verify the user
        user.backend = 'users.backends.PhoneNumberBackend'
        login(request, user)
        request.session.save()
        
        logger.info(f"Google user authenticated and session created: {user.email} (Session: {request.session.session_key})")
        
        # Get CSRF token for secure requests
        csrf_token = get_token(request)
        
        response = JsonResponse({
            'message': 'Google authentication successful',
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'phone_number': user.phone_number,
                'kyc_verified': user.kyc_verified,
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'picture': user.picture,
            },
            'csrf_token': csrf_token
        }, status=200)
        
        logger.info(f"Google login response ready for {user.email}")
        
        return response
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Google auth error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

