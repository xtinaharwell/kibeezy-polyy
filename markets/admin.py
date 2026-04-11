from django.contrib import admin
from django.utils.safestring import mark_safe
from django import forms
from decimal import Decimal
from .models import Market, Bet, PriceHistory, ChatMessage
from .amm import AMM


class MarketAdminForm(forms.ModelForm):
    """Custom form for Market admin with bootstrap liquidity amount field"""
    liquidity_amount = forms.DecimalField(
        required=False,
        initial=100000,
        help_text="Total liquidity to bootstrap (will be split 50/50 between YES and NO). Only used when is_bootstrapped is checked.",
        widget=forms.NumberInput(attrs={'min': 1000, 'step': 1000})
    )
    
    class Meta:
        model = Market
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial liquidity amount if market is already bootstrapped
        if self.instance and self.instance.is_bootstrapped and self.instance.yes_reserve:
            self.fields['liquidity_amount'].initial = (self.instance.yes_reserve + self.instance.no_reserve) * 2
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Handle bootstrap logic
        if self.cleaned_data.get('is_bootstrapped') and not instance.is_bootstrapped:
            # Market is being bootstrapped for the first time
            liquidity_amount = self.cleaned_data.get('liquidity_amount') or Decimal('100000')
            liquidity = Decimal(str(liquidity_amount))
            
            if liquidity > 0:
                half_liquidity = liquidity / Decimal('2')
                instance.yes_reserve = half_liquidity
                instance.no_reserve = half_liquidity
                instance.yes_probability = 50
        
        if commit:
            instance.save()
        return instance


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    form = MarketAdminForm
    
    list_display = ('question', 'category', 'status', 'market_type', 'yes_probability', 'volume', 'bootstrap_status', 'created_at')
    list_filter = ('status', 'category', 'market_type', 'is_bootstrapped', 'created_at')
    search_fields = ('question', 'description')
    readonly_fields = ('created_at', 'amm_status_display', 'amm_reserves_display')
    
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
            'fields': ('is_bootstrapped', 'liquidity_amount', 'amm_status_display', 'yes_reserve', 'no_reserve', 'amm_reserves_display'),
            'description': 'Check "is_bootstrapped" and set a liquidity amount to initialize AMM for this market. The amount will be split 50/50 between YES and NO reserves.'
        }),
        ('Statistics', {
            'fields': ('volume',)
        }),
    )
    
    date_hierarchy = 'created_at'
    
    def bootstrap_status(self, obj):
        """Display bootstrap status with colored indicator"""
        if obj.is_bootstrapped:
            return mark_safe(
                '<span style="color: green; font-weight: bold;">✓ Bootstrapped</span>'
            )
        return mark_safe(
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
                return mark_safe(
                    '<div><strong>Active</strong><br/>Current Price: {:.1f}%</div>'.format(current_price)
                )
            except Exception as e:
                return mark_safe('<span style="color: red;">Error: {}</span>'.format(str(e)))
        return "Reserves not properly initialized"
    amm_status_display.short_description = 'AMM Status'
    
    def amm_reserves_display(self, obj):
        """Display AMM reserves"""
        if obj.is_bootstrapped:
            html = '<div>YES Reserve: <strong>{}</strong> KES<br/>NO Reserve: <strong>{}</strong> KES<br/>Product (k): <strong>{}</strong></div>'.format(
                float(obj.yes_reserve),
                float(obj.no_reserve),
                float(obj.yes_reserve * obj.no_reserve) if obj.yes_reserve > 0 and obj.no_reserve > 0 else 0
            )
            return mark_safe(html)
        return "Not bootstrapped"
    amm_reserves_display.short_description = 'Reserve Details'


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
