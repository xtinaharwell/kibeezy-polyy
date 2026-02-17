from django.urls import path
from notifications.views import get_notifications, mark_notification_read, mark_all_read

urlpatterns = [
    path('notifications/', get_notifications, name='get_notifications'),
    path('notifications/<int:notification_id>/read/', mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', mark_all_read, name='mark_all_read'),
]
