"""
Django management command to normalize all existing phone numbers in the database.
Converts all phone numbers to international format (254xxxxxxxxx).
"""
from django.core.management.base import BaseCommand
from users.models import CustomUser
from api.validators import normalize_phone_number
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Normalize all phone numbers to international format (254xxxxxxxxx)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting phone number normalization...'))
        
        users = CustomUser.objects.filter(phone_number__isnull=False)
        updated_count = 0
        failed_count = 0
        
        for user in users:
            original_phone = user.phone_number
            try:
                # Normalize the phone number
                normalized_phone = normalize_phone_number(original_phone)
                
                # Only update if changed
                if original_phone != normalized_phone:
                    user.phone_number = normalized_phone
                    user.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Updated: {original_phone} → {normalized_phone}'
                        )
                    )
                    logger.info(f'Phone number normalized: {original_phone} → {normalized_phone}')
                else:
                    self.stdout.write(f'  Skipped: {original_phone} (already normalized)')
                    
            except Exception as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed: {original_phone} - {str(e)}')
                )
                logger.error(f'Failed to normalize {original_phone}: {str(e)}')

        self.stdout.write(self.style.SUCCESS(f'\n✓ Normalization complete!'))
        self.stdout.write(f'  Updated: {updated_count} users')
        self.stdout.write(f'  Failed: {failed_count} users')
        self.stdout.write(f'  Total processed: {users.count()} users')
