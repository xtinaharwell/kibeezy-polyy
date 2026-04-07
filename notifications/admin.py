from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('user__phone_number', 'title', 'message')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Notification Content', {
            'fields': ('user', 'type_choice', 'title', 'message')
        }),
        ('Styling', {
            'fields': ('color_class',),
            'classes': ('collapse',)
        }),
        ('Related Items', {
            'fields': ('related_market', 'related_bet'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Dates', {
            'fields': ('created_at',)
        }),
    )
    date_hierarchy = 'created_at'
