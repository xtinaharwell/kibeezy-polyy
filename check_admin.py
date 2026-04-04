import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from users.models import CustomUser

# Get the superuser
admin = CustomUser.objects.filter(is_superuser=True).first()

if admin:
    print(f"Admin Phone: {admin.phone_number}")
    print(f"Admin Name: {admin.full_name}")
    print(f"is_staff: {admin.is_staff}")
    print(f"is_superuser: {admin.is_superuser}")
    print(f"is_active: {admin.is_active}")
    
    # Fix if needed
    if not admin.is_staff:
        print("\n❌ ISSUE: Admin is_staff is False! Fixing...")
        admin.is_staff = True
        admin.save()
        print("✅ Fixed! Admin is_staff is now True")
else:
    print("No superuser found!")
