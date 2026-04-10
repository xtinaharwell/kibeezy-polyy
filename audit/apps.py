"""
Django app configuration for audit trail system.
"""

from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit'
    verbose_name = 'Audit Trail'
    
    def ready(self):
        """Register signal handlers when app loads"""
        import audit.signals  # Connect Django signals
