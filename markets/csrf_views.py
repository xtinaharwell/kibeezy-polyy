"""
CSRF Token Endpoint

Provides CSRF tokens to the frontend for API requests.
This ensures Django's CSRF protection works correctly with Next.js frontend.
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.middleware.csrf import get_token


@api_view(['GET'])
def get_csrf_token(request):
    """
    Get CSRF token for the current session.
    
    Django automatically sets the csrftoken cookie when this endpoint is called.
    The frontend should extract this and include it in the X-CSRFToken header
    for all POST/PUT/DELETE requests.
    
    Response:
    {
        "csrfToken": "token_value"
    }
    """
    csrf_token = get_token(request)
    return Response({
        'csrfToken': csrf_token,
        'message': 'CSRF token retrieved. Include in X-CSRFToken header for POST requests.'
    })
