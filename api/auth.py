"""
Custom authentication utilities for handling session-based auth in CORS requests
"""
from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.models import AnonymousUser
from django.middleware.csrf import CsrfViewMiddleware


def require_auth(view_func):
    """
    Decorator that ensures a view requires authentication.
    Works with session-based auth in CORS requests.
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        # Check if user is authenticated via session
        if request.user and request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        
        # If not authenticated, return 401
        return JsonResponse(
            {'error': 'Authentication required'}, 
            status=401
        )
    
    return wrapped
