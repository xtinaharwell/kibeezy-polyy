from django.contrib.auth.backends import ModelBackend
from .models import CustomUser


class PhoneNumberBackend(ModelBackend):
    """
    Authenticate using phone_number instead of username
    Allows superusers to login to admin without requiring is_staff flag
    """
    def authenticate(self, request, phone_number=None, password=None, **kwargs):
        try:
            user = CustomUser.objects.get(phone_number=phone_number)
        except CustomUser.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None

    def user_can_authenticate(self, user):
        """
        Allow superusers and active users to authenticate
        Django admin requires is_active=True, but we allow superusers regardless of is_staff
        """
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None


class AdminPhoneBackend(ModelBackend):
    """
    Custom backend for Django admin that allows superusers without is_staff
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Try to get user by phone_number (since we use phone as username)
        try:
            user = CustomUser.objects.get(phone_number=username)
        except CustomUser.DoesNotExist:
            return None

        # Allow if password is correct and user is either:
        # 1. Staff with is_active=True, OR
        # 2. Superuser (regardless of is_staff)
        if user.check_password(password):
            if user.is_active and (user.is_staff or user.is_superuser):
                return user
        return None

    def get_user(self, user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None
