"""
Django Admin customization for Audit models
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import AuditLog, AuditSummary, AccessLog, AuditAlert


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'action_display', 'severity_bar', 'object_display', 'user_display', 
                    'created_at', 'hash_status')
    list_filter = ('action', 'severity', 'content_type', 'created_at')
    search_fields = ('object_id', 'user__phone_number', 'description')
    date_hierarchy = 'created_at'
    
    readonly_fields = ('current_hash', 'previous_hash', 'hash_verified', 'created_at', 
                       'action', 'content_type', 'object_id', 'changes', 'before_values', 
                       'after_values')
    
    fieldsets = (
        ('Action Details', {
            'fields': ('action', 'severity', 'description', 'content_type', 'object_id', 'object_repr'),
        }),
        ('Actor Information', {
            'fields': ('user', 'ip_address', 'user_agent'),
        }),
        ('Changes', {
            'fields': ('changes', 'before_values', 'after_values'),
            'classes': ('collapse',),
        }),
        ('Integrity', {
            'fields': ('current_hash', 'previous_hash', 'hash_verified'),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'related_transaction'),
        }),
    )
    
    def action_display(self, obj):
        """Display action with color coding"""
        colors = {
            'CREATE': 'green',
            'UPDATE': 'blue',
            'DELETE': 'red',
            'DEPOSIT': 'green',
            'WITHDRAWAL': 'orange',
            'PAYOUT_ISSUED': 'purple',
        }
        color = colors.get(obj.action, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.action
        )
    
    def severity_bar(self, obj):
        """Display severity as colored bar"""
        colors = {
            'LOW': '#2ecc71',
            'MEDIUM': '#f39c12',
            'HIGH': '#e74c3c',
            'CRITICAL': '#8b0000',
        }
        color = colors.get(obj.severity, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.severity
        )
    
    def object_display(self, obj):
        """Display the affected object"""
        return f"{obj.content_type}: {obj.object_repr[:50]}"
    
    def user_display(self, obj):
        """Display the user who made the change"""
        if obj.user:
            return obj.user.phone_number
        return 'System'
    
    def hash_status(self, obj):
        """Display hash verification status"""
        verified = obj.verify_hash()
        if verified:
            return format_html('<span style="color: green;">✅ Verified</span>')
        else:
            return format_html('<span style="color: red;">❌ FAILED</span>')
    
    def has_add_permission(self, request):
        """Prevent manual creation of audit logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of audit logs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent modification of audit logs"""
        return False


@admin.register(AuditAlert)
class AuditAlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'alert_type', 'severity_badge', 'user_display', 'acknowledged_status', 'created_at')
    list_filter = ('alert_type', 'severity', 'acknowledged', 'resolved', 'created_at')
    search_fields = ('description', 'user__phone_number')
    date_hierarchy = 'created_at'
    
    readonly_fields = ('created_at', 'alert_type', 'description')
    
    fieldsets = (
        ('Alert Details', {
            'fields': ('alert_type', 'severity', 'description', 'user'),
        }),
        ('Response', {
            'fields': ('acknowledged', 'acknowledged_by', 'acknowledged_at', 'resolved'),
        }),
        ('Investigation', {
            'fields': ('notes', 'action_taken', 'related_logs'),
        }),
        ('Metadata', {
            'fields': ('created_at',),
        }),
    )
    
    def severity_badge(self, obj):
        """Display severity as colored badge"""
        colors = {
            'LOW': '#2ecc71',
            'MEDIUM': '#f39c12',
            'HIGH': '#e74c3c',
            'CRITICAL': '#8b0000',
        }
        color = colors.get(obj.severity, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold;">{}</span>',
            color,
            obj.severity
        )
    
    def user_display(self, obj):
        if obj.user:
            return obj.user.phone_number
        return 'N/A'
    
    def acknowledged_status(self, obj):
        if obj.acknowledged:
            return format_html('<span style="color: green;">✅ Acknowledged</span>')
        else:
            return format_html('<span style="color: red;">⏳ Pending</span>')
    
    actions = ['mark_acknowledged']
    
    def mark_acknowledged(self, request, queryset):
        """Bulk action to acknowledge alerts"""
        updated = 0
        for alert in queryset:
            if not alert.acknowledged:
                alert.acknowledge(request.user, 'Bulk acknowledged')
                updated += 1
        self.message_user(request, f'{updated} alerts acknowledged')
    mark_acknowledged.short_description = 'Mark selected alerts as acknowledged'


@admin.register(AuditSummary)
class AuditSummaryAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_actions', 'critical_count', 'high_count', 'unique_users', 'total_amount_processed')
    list_filter = ('date',)
    date_hierarchy = 'date'
    
    readonly_fields = ('date', 'total_actions', 'creates', 'updates', 'deletes', 
                      'financial_actions', 'admin_actions', 'critical_count', 'high_count',
                      'unique_users', 'total_amount_processed', 'created_at', 'updated_at')
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('user_display', 'resource_type', 'resource_id', 'ip_address', 'status_code', 'accessed_at')
    list_filter = ('resource_type', 'success', 'status_code', 'accessed_at')
    search_fields = ('user__phone_number', 'ip_address', 'resource_id')
    date_hierarchy = 'accessed_at'
    
    readonly_fields = ('user', 'resource_type', 'resource_id', 'ip_address', 'user_agent',
                      'query_params', 'status_code', 'success', 'accessed_at')
    
    def user_display(self, obj):
        return obj.user.phone_number if obj.user else 'Anonymous'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
