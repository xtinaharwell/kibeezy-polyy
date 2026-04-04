from django.urls import path
from . import views

urlpatterns = [
    # User endpoints
    path('my-tickets/', views.get_my_tickets, name='get_my_tickets'),
    path('tickets/<str:ticket_id>/', views.get_ticket_detail, name='get_ticket_detail'),
    path('create/', views.create_support_ticket, name='create_support_ticket'),
    path('tickets/<str:ticket_id>/reply/', views.add_message_to_ticket, name='add_message_to_ticket'),
    
    # Support staff endpoints
    path('dashboard/tickets/', views.support_dashboard_tickets, name='support_dashboard_tickets'),
    path('dashboard/tickets/<str:ticket_id>/', views.support_dashboard_ticket_detail, name='support_dashboard_ticket_detail'),
    path('dashboard/tickets/<str:ticket_id>/update/', views.update_ticket, name='update_ticket'),
    path('dashboard/tickets/<str:ticket_id>/support-reply/', views.support_reply, name='support_reply'),
    path('dashboard/support-staff/', views.support_staff_list, name='support_staff_list'),
]
