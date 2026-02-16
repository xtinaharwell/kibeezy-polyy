# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
try:
    from .celery import app as celery_app
except ImportError:
    # Celery not installed yet (during development setup)
    celery_app = None

__all__ = ('celery_app',)
