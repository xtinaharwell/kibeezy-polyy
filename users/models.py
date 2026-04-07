from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator

class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number=None, full_name=None, password=None, **extra_fields):
        # For Google OAuth users: phone_number and password are optional
        # For phone-based auth: phone_number and password are required
        
        google_id = extra_fields.get('google_id')
        email = extra_fields.get('email')
        
        # If not a Google OAuth user, require phone_number
        if not google_id and not phone_number:
            raise ValueError('The Phone Number must be set for non-OAuth users')
        
        # Require full_name for all users
        if not full_name:
            raise ValueError('Full name must be set')
        
        user = self.model(phone_number=phone_number, full_name=full_name, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone_number, full_name, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '0718693484'.")
    phone_number = models.CharField(validators=[phone_regex], max_length=17, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, null=True, blank=True)
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    picture = models.URLField(null=True, blank=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    kyc_verified = models.BooleanField(default=False)
    kyc_verified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_support_staff = models.BooleanField(default=False, help_text="User can view and respond to support tickets")
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['full_name']

    def __str__(self):
        # Return phone number if available, otherwise email, otherwise full name
        if self.phone_number:
            return self.phone_number
        elif self.email:
            return self.email
        else:
            return self.full_name
    
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
