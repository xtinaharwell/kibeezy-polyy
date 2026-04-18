"""
API views for Kibeezy Poly backend.
"""

from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect


@csrf_protect
@require_http_methods(["GET"])
def get_csrf_token(request):
    """
    Endpoint to retrieve CSRF token for AJAX requests.
    This allows JavaScript to get a CSRF token for POST/PUT/DELETE operations.
    """
    token = get_token(request)
    return JsonResponse({
        'csrfToken': token
    })


def csrf_failure(request, reason=""):
    """
    Handle CSRF failures gracefully by returning JSON.
    """
    return JsonResponse(
        {
            'error': 'CSRF validation failed',
            'reason': reason,
        },
        status=403
    )
