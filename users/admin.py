from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('phone_number', 'full_name', 'balance', 'kyc_verified', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_support_staff', 'kyc_verified', 'date_joined')
    search_fields = ('phone_number', 'full_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'balance')}),
        ('KYC Verification', {'fields': ('kyc_verified', 'kyc_verified_at')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_support_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'full_name', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login', 'kyc_verified_at')
