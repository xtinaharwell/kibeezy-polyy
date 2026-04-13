"""
API views for Kibeezy Poly backend.
"""

from django.http import JsonResponse


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
