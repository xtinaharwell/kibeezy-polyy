"""
Rate limiting utilities for expensive operations
Implements token bucket algorithm for flexible rate limiting
"""
import time
import hashlib
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter using Django cache"""
    
    def __init__(self, max_requests, window_seconds):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Number of requests allowed
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def get_key(self, identifier):
        """Generate cache key for rate limiting"""
        return f"rate_limit:{identifier}"
    
    def is_allowed(self, identifier):
        """
        Check if request is allowed
        
        Args:
            identifier: Unique identifier (user_id, IP, etc)
            
        Returns:
            tuple: (allowed: bool, remaining: int, reset_at: int)
        """
        key = self.get_key(identifier)
        now = time.time()
        
        # Get current request data from cache
        request_data = cache.get(key, {'requests': [], 'window_start': now})
        
        # Remove old requests outside the window
        window_start = request_data.get('window_start', now)
        requests = [
            req_time for req_time in request_data.get('requests', [])
            if req_time > now - self.window_seconds
        ]
        
        # Check if limit exceeded
        if len(requests) >= self.max_requests:
            reset_at = int(requests[0] + self.window_seconds)
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False, 0, reset_at
        
        # Add new request
        requests.append(now)
        remaining = self.max_requests - len(requests)
        reset_at = int(now + self.window_seconds)
        
        # Store in cache for the window duration
        cache.set(key, {
            'requests': requests,
            'window_start': window_start
        }, self.window_seconds + 1)
        
        return True, remaining, reset_at


def get_client_identifier(request):
    """
    Extract unique identifier for rate limiting
    Priority: user_id > authenticated email > IP address
    """
    # Use authenticated user ID (most specific)
    if request.user and request.user.is_authenticated:
        return f"user_{request.user.id}"
    
    # Use email header for OAuth users
    email = request.headers.get('X-User-Email')
    if email:
        return f"email_{hashlib.md5(email.encode()).hexdigest()}"
    
    # Use phone number header
    phone = request.headers.get('X-User-Phone-Number')
    if phone:
        return f"phone_{hashlib.md5(phone.encode()).hexdigest()}"
    
    # Fall back to IP address
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        return f"ip_{x_forwarded_for.split(',')[0]}"
    
    return f"ip_{request.META.get('REMOTE_ADDR')}"


def rate_limit(max_requests, window_seconds, key_func=None):
    """
    Decorator for rate limiting endpoints
    
    Usage:
        @rate_limit(max_requests=50, window_seconds=3600)  # 50 per hour
        def place_bet(request):
            ...
    
    Args:
        max_requests: Number of requests allowed
        window_seconds: Time window in seconds (e.g., 3600 = 1 hour)
        key_func: Optional custom function to extract rate limit key
    """
    limiter = RateLimiter(max_requests, window_seconds)
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get identifier for this request
            if key_func:
                identifier = key_func(request)
            else:
                identifier = get_client_identifier(request)
            
            # Check rate limit
            allowed, remaining, reset_at = limiter.is_allowed(identifier)
            
            if not allowed:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Rate limit exceeded',
                    'reset_at': reset_at,
                    'retry_after': reset_at - int(time.time())
                }, status=429)  # 429 Too Many Requests
            
            # Add rate limit headers to response
            response = view_func(request, *args, **kwargs)
            
            if isinstance(response, JsonResponse):
                response['X-RateLimit-Limit'] = str(limiter.max_requests)
                response['X-RateLimit-Remaining'] = str(remaining)
                response['X-RateLimit-Reset'] = str(reset_at)
            
            return response
        
        return wrapper
    
    return decorator


def rate_limit_auth_attempts(view_func):
    """
    Specialized rate limiter for authentication attempts
    Limits to 5 attempts per 15 minutes per identifier
    Triggers account lockout if exceeded
    """
    limiter = RateLimiter(max_requests=5, window_seconds=15 * 60)
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        identifier = get_client_identifier(request)
        allowed, remaining, reset_at = limiter.is_allowed(identifier)
        
        if not allowed:
            logger.warning(f"Authentication rate limit exceeded for {identifier}")
            return JsonResponse({
                'status': 'error',
                'message': 'Too many authentication attempts. Please try again later.',
                'reset_at': reset_at,
                'retry_after': reset_at - int(time.time())
            }, status=429)
        
        response = view_func(request, *args, **kwargs)
        
        if isinstance(response, JsonResponse):
            response['X-RateLimit-Remaining'] = str(remaining)
        
        return response
    
    return wrapper


def rate_limit_payments(view_func):
    """
    Specialized rate limiter for payment operations
    Limits to 10 payment attempts per hour per user
    """
    limiter = RateLimiter(max_requests=10, window_seconds=3600)
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        identifier = get_client_identifier(request)
        allowed, remaining, reset_at = limiter.is_allowed(identifier)
        
        if not allowed:
            logger.warning(f"Payment rate limit exceeded for {identifier}")
            return JsonResponse({
                'status': 'error',
                'message': 'Too many payment attempts. Please try again later.',
                'reset_at': reset_at,
                'retry_after': reset_at - int(time.time())
            }, status=429)
        
        response = view_func(request, *args, **kwargs)
        return response
    
    return wrapper
