"""
Celery configuration for KASOKO
Handles async tasks like market settlement and M-Pesa B2C payouts
"""
import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

app = Celery('kibeezy_poly')

# Load configuration from Django settings with CELERY prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# Default task configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task timeouts and retries
    task_soft_time_limit=600,  # 10 minutes soft limit
    task_time_limit=900,  # 15 minutes hard limit
    
    # Result backend (Redis) retention
    result_expires=3600,  # Expire results after 1 hour
    
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
