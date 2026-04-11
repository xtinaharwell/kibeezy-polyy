from django.contrib import admin
from django.utils.html import format_html
from decimal import Decimal
from .models import Market, Bet, PriceHistory, ChatMessage
from .amm import AMM


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'status', 'market_type', 'yes_probability', 'volume', 'bootstrap_status', 'created_at')
    list_filter = ('status', 'category', 'market_type', 'is_bootstrapped', 'created_at')
    search_fields = ('question', 'description')
    readonly_fields = ('created_at', 'amm_status_display', 'amm_reserves_display', 'is_bootstrapped')
    actions = ['bootstrap_market_action']
    
    fieldsets = (
        ('Market Info', {
            'fields': ('question', 'description', 'category', 'image_url')
        }),
        ('Market Configuration', {
            'fields': ('market_type', 'yes_probability', 'options')
        }),
        ('Status & Dates', {
            'fields': ('status', 'end_date', 'created_at', 'resolved_at', 'resolved_outcome')
        }),
        ('AMM Configuration', {
            'fields': ('is_bootstrapped', 'amm_status_display', 'yes_reserve', 'no_reserve', 'amm_reserves_display'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('volume',)
        }),
    )
    date_hierarchy = 'created_at'
    
    def bootstrap_status(self, obj):
        """Display bootstrap status with colored indicator"""
        if obj.is_bootstrapped:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Bootstrapped</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Not Bootstrapped</span>'
        )
    bootstrap_status.short_description = 'Bootstrap Status'
    
    def amm_status_display(self, obj):
        """Display current AMM status"""
        if not obj.is_bootstrapped:
            return "Market not bootstrapped. Click 'Bootstrap Market' action to initialize AMM."
        
        if obj.yes_reserve > 0 and obj.no_reserve > 0:
            try:
                amm = AMM(obj.yes_reserve, obj.no_reserve)
                current_price = amm.get_current_price()
                return format_html(
                    '<div><strong>Active</strong><br/>Current Price: {:.1f}%</div>',
                    current_price
                )
            except Exception as e:
                return format_html(f'<span style="color: red;">Error: {str(e)}</span>')
        return "Reserves not properly initialized"
    amm_status_display.short_description = 'AMM Status'
    
    def amm_reserves_display(self, obj):
        """Display AMM reserves"""
        if obj.is_bootstrapped:
            return format_html(
                '<div>YES Reserve: <strong>{}</strong> KES<br/>NO Reserve: <strong>{}</strong> KES<br/>Product (k): <strong>{}</strong></div>',
                float(obj.yes_reserve),
                float(obj.no_reserve),
                float(obj.yes_reserve * obj.no_reserve) if obj.yes_reserve > 0 and obj.no_reserve > 0 else 0
            )
        return "Not bootstrapped"
    amm_reserves_display.short_description = 'Reserve Details'
    
    def bootstrap_market_action(self, request, queryset):
        """Admin action to bootstrap markets"""
        bootstrapped_count = 0
        skipped_count = 0
        
        for market in queryset:
            if market.is_bootstrapped:
                skipped_count += 1
                continue
            
            # Bootstrap with default 100K liquidity (50K YES, 50K NO)
            liquidity = Decimal('100000')
            half_liquidity = liquidity / Decimal('2')
            
            market.yes_reserve = half_liquidity
            market.no_reserve = half_liquidity
            market.is_bootstrapped = True
            market.yes_probability = 50
            market.save()
            bootstrapped_count += 1
        
        if bootstrapped_count > 0:
            self.message_user(request, f'Successfully bootstrapped {bootstrapped_count} market(s) with 100K KES liquidity.')
        if skipped_count > 0:
            self.message_user(request, f'{skipped_count} market(s) were already bootstrapped.', level='WARNING')
    
    bootstrap_market_action.short_description = 'Bootstrap selected markets with 100K KES liquidity'


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'outcome', 'amount', 'action', 'entry_probability', 'timestamp')
    list_filter = ('outcome', 'action', 'order_type', 'timestamp')
    search_fields = ('user__phone_number', 'market__question', 'id')
    readonly_fields = ('timestamp',)
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
            'fields': ('timestamp',)
        }),
    )
    date_hierarchy = 'timestamp'


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('market', 'option_id', 'yes_probability', 'no_probability', 'timestamp')
    list_filter = ('market', 'option_id', 'timestamp')
    search_fields = ('market__question',)
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'message_preview', 'created_at')
    list_filter = ('market', 'created_at')
    search_fields = ('user__phone_number', 'market__question', 'message')
    readonly_fields = ('created_at',)
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'
