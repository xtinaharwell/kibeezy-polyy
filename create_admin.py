import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from users.models import CustomUser

# Create superuser
phone = '0712345678'
name = 'Kibeezy'
password = 'SecureAdmin@2026'

# Check if user already exists
if CustomUser.objects.filter(phone_number=phone).exists():
    print(f"User with phone {phone} already exists. Deleting and recreating...")
    CustomUser.objects.filter(phone_number=phone).delete()

# Create superuser
superuser = CustomUser.objects.create_superuser(
    phone_number=phone,
    full_name=name,
    password=password
)

print(f"✅ Superuser created successfully!")
print(f"Phone: {phone}")
print(f"Name: {name}")
print(f"Password: {password}")
print(f"Is Staff: {superuser.is_staff}")
print(f"Is Superuser: {superuser.is_superuser}")
