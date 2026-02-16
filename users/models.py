from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator

class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, full_name, pin=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number must be set')
        user = self.model(phone_number=phone_number, full_name=full_name, **extra_fields)
        if pin:
            user.set_password(pin) # Use PIN as password
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        # Handle both 'password' (from Django command) and 'pin' (legacy)
        pin = extra_fields.pop('pin', password)
        return self.create_user(phone_number, full_name, pin, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '0718693484'.")
    phone_number = models.CharField(validators=[phone_regex], max_length=17, unique=True)
    full_name = models.CharField(max_length=255)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    kyc_verified = models.BooleanField(default=False)
    kyc_verified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['full_name']

    def __str__(self):
        return self.phone_number
    
    def get_user_statistics(self):
        """Get user statistics: total wagered, wins, losses"""
        from markets.models import Bet
        bets = Bet.objects.filter(user=self)
        total_wagered = sum(float(bet.amount) for bet in bets if bet.result != 'PENDING')
        won_bets = bets.filter(result='WON').count()
        lost_bets = bets.filter(result='LOST').count()
        win_rate = (won_bets / (won_bets + lost_bets) * 100) if (won_bets + lost_bets) > 0 else 0
        return {
            'total_wagered': total_wagered,
            'wins': won_bets,
            'losses': lost_bets,
            'win_rate': round(win_rate, 2)
        }
