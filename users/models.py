from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator

class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, full_name, pin, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number must be set')
        user = self.model(phone_number=phone_number, full_name=full_name, **extra_fields)
        user.set_password(pin) # Use PIN as password
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, full_name, pin, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone_number, full_name, pin, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '0718693484'.")
    phone_number = models.CharField(validators=[phone_regex], max_length=17, unique=True)
    full_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['full_name']

    def __str__(self):
        return self.phone_number
