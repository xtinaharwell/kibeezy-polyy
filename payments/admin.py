from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'amount', 'status', 'phone_number', 'created_at')
    list_filter = ('type', 'status', 'created_at')
    search_fields = ('user__phone_number', 'phone_number', 'description')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Transaction Info', {
            'fields': ('user', 'type', 'amount', 'status')
        }),
        ('Details', {
            'fields': ('description', 'phone_number', 'related_bet')
        }),
        ('MPesa Data', {
            'fields': ('checkout_request_id', 'merchant_request_id', 'external_ref', 'reference', 'mpesa_response'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at',)
        }),
    )
    date_hierarchy = 'created_at'
