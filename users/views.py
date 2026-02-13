import json
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import CustomUser

@csrf_exempt
def signup_view(request):
    if request.method == 'POST':
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
            return JsonResponse({'message': 'Account created successfully', 'user': {'phone_number': user.phone_number, 'full_name': user.full_name}}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone_number')
            pin = data.get('pin')

            if not all([phone_number, pin]):
                return JsonResponse({'error': 'Missing credentials'}, status=400)

            user = authenticate(request, phone_number=phone_number, password=pin)
            if user is not None:
                login(request, user)
                return JsonResponse({'message': 'Login successful', 'user': {'phone_number': user.phone_number, 'full_name': user.full_name}})
            else:
                return JsonResponse({'error': 'Invalid phone number or PIN'}, status=401)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)
