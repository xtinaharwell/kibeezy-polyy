import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Simple health check endpoint to verify backend is running"""
    return JsonResponse({
        'status': 'ok',
        'message': 'Backend is running',
        'api_url': 'http://127.0.0.1:8000'
    }, status=200)
