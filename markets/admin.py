from django.contrib import admin
from .models import Market, Bet, PriceHistory, ChatMessage


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'status', 'market_type', 'yes_probability', 'volume', 'created_at')
    list_filter = ('status', 'category', 'market_type', 'created_at')
    search_fields = ('question', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Market Info', {
            'fields': ('question', 'description', 'category', 'image_url')
        }),
        ('Market Configuration', {
            'fields': ('market_type', 'yes_probability', 'options')
        }),
        ('Status & Dates', {
            'fields': ('status', 'end_date', 'created_at', 'updated_at', 'resolved_at', 'resolved_outcome')
        }),
        ('Statistics', {
            'fields': ('volume', 'total_wagered', 'yes_bets', 'no_bets')
        }),
    )
    date_hierarchy = 'created_at'


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'outcome', 'amount', 'action', 'entry_probability', 'created_at')
    list_filter = ('outcome', 'action', 'order_type', 'created_at')
    search_fields = ('user__phone_number', 'market__question', 'id')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Bet Details', {
            'fields': ('user', 'market', 'outcome', 'amount', 'action')
        }),
        ('Option Info', {
            'fields': ('option_id', 'option_label'),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': ('entry_probability', 'order_type', 'limit_price', 'quantity')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    date_hierarchy = 'created_at'


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('market', 'yes_probability', 'no_probability', 'timestamp')
    list_filter = ('market', 'timestamp')
    search_fields = ('market__question',)
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'message_preview', 'created_at')
    list_filter = ('market', 'created_at')
    search_fields = ('user__phone_number', 'market__question', 'message')
    readonly_fields = ('created_at', 'updated_at')
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'
