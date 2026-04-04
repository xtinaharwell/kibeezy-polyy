from django.contrib import admin
from .models import SupportTicket, SupportMessage

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'subject', 'user', 'assigned_to', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'assigned_to']
    search_fields = ['ticket_id', 'subject', 'user__phone_number', 'user__full_name']
    readonly_fields = ['ticket_id', 'created_at', 'updated_at', 'resolved_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Ticket Info', {
            'fields': ('ticket_id', 'subject', 'status')
        }),
        ('Assignment', {
            'fields': ('user', 'assigned_to')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser and request.user.is_support_staff:
            # Support staff see all tickets and their assigned ones highlighted
            return qs
        return qs


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'ticket', 'sender', 'is_from_user', 'created_at']
    list_filter = ['is_from_user', 'created_at', 'ticket__status']
    search_fields = ['ticket__ticket_id', 'message', 'sender__phone_number', 'sender__full_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Ticket', {
            'fields': ('ticket',)
        }),
        ('Message', {
            'fields': ('sender', 'message', 'is_from_user')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new message
            obj.sender = request.user
            obj.is_from_user = False  # Messages created by admin are from support team
        super().save_model(request, obj, form, change)
