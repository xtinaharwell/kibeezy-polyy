from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from users.models import CustomUser


class Command(BaseCommand):
    help = 'Set default password for all existing users'

    def handle(self, *args, **options):
        default_password = 'password123'
        hashed_password = make_password(default_password)
        
        user_count = CustomUser.objects.all().count()
        CustomUser.objects.all().update(password=hashed_password)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Set default password "password123" for {user_count} existing users'
            )
        )
