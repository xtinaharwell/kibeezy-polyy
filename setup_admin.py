from users.models import CustomUser

# Make user 0718693484 a superuser and staff
try:
    user = CustomUser.objects.get(phone_number="0718693484")
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f"✓ User {user.full_name} ({user.phone_number}) is now a superuser and staff")
except CustomUser.DoesNotExist:
    print("✗ User with phone number 0718693484 not found")
except Exception as e:
    print(f"✗ Error: {str(e)}")

# Create/update Django admin superuser
try:
    admin_user, created = CustomUser.objects.get_or_create(
        phone_number="django_admin",
        defaults={
            'full_name': 'Django Admin',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    
    if not created:
        admin_user.is_staff = True
        admin_user.is_superuser = True
    
    # Set password
    admin_user.set_password("#collins12K")
    admin_user.save()
    
    status = "created" if created else "updated"
    print(f"✓ Django admin user {status}")
    print(f"  Phone: django_admin")
    print(f"  Password: #collins12K")
    
except Exception as e:
    print(f"✗ Error creating admin user: {str(e)}")
