import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from users.models import CustomUser

u = CustomUser.objects.get(phone_number='0718693484')
u.is_staff = True
u.is_superuser = True
u.save()
print(f'✓ {u.phone_number} is now admin (is_staff={u.is_staff}, is_superuser={u.is_superuser})')
