"""
Audit URL routing
"""

from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    # Audit log endpoints
    path('logs/', views.view_audit_logs, name='logs'),
    path('logs/<int:log_id>/', views.audit_log_detail, name='log_detail'),
    path('logs/verify-chain/', views.verify_audit_chain, name='verify_chain'),
    
    # Summary reports
    path('summary/', views.audit_summary, name='summary'),
    
    # Alerts
    path('alerts/', views.audit_alerts, name='alerts'),
    path('alerts/<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    
    # User activity
    path('user/<str:user_phone>/activity/', views.user_activity_report, name='user_activity'),
]
