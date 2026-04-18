from django.urls import path
from .views import list_markets, place_bet, market_chat, market_details, get_price_history, preview_trade_price, get_user_available_shares
from .dashboard_views import user_dashboard, transaction_history, initiate_withdrawal
from .admin_views import admin_markets, resolve_market, create_market, delete_market
from .analytics_views import analytics_dashboard, risk_dashboard
from .liquidity_views import (
    deposit_liquidity_view,
    withdraw_liquidity_view,
    claim_fees_view,
    get_user_lp_positions,
    get_liquidity_pool_stats,
    get_lp_analytics,
    get_pool_risk_score,
    get_fee_analytics_dashboard,
    get_portfolio_il_analysis,
)

urlpatterns = [
    path('', list_markets, name='list_markets'),
    path('bet/', place_bet, name='place_bet'),
    path('<int:market_id>/chat/', market_chat, name='market_chat'),
    path('<int:market_id>/details/', market_details, name='market_details'),
    path('<int:market_id>/price-history/', get_price_history, name='price_history'),
    path('<int:market_id>/available-shares/', get_user_available_shares, name='available_shares'),
    path('preview-price/', preview_trade_price, name='preview_price'),
    
    # Liquidity provider endpoints
    path('liquidity/deposit/', deposit_liquidity_view, name='liquidity_deposit'),
    path('liquidity/withdraw/', withdraw_liquidity_view, name='liquidity_withdraw'),
    path('liquidity/claim-fees/', claim_fees_view, name='claim_fees'),
    path('liquidity/positions/', get_user_lp_positions, name='lp_positions'),
    path('liquidity/pool-stats/', get_liquidity_pool_stats, name='pool_stats'),
    path('liquidity/analytics/', get_lp_analytics, name='lp_analytics'),
    path('liquidity/risk-score/', get_pool_risk_score, name='pool_risk_score'),
    path('liquidity/fee-analytics/', get_fee_analytics_dashboard, name='fee_analytics'),
    path('liquidity/il-analysis/', get_portfolio_il_analysis, name='il_analysis'),
    
    # Dashboard endpoints
    path('dashboard/', user_dashboard, name='user_dashboard'),
    path('history/', transaction_history, name='transaction_history'),
    path('withdraw/', initiate_withdrawal, name='initiate_withdrawal'),
    
    # Admin endpoints
    path('admin/markets/', admin_markets, name='admin_markets'),
    path('admin/markets/<int:market_id>/', delete_market, name='delete_market'),
    path('admin/resolve/', resolve_market, name='resolve_market'),
    path('admin/create/', create_market, name='create_market'),
    
    # Analytics endpoints
    path('admin/analytics/', analytics_dashboard, name='analytics_dashboard'),
    path('admin/risk/', risk_dashboard, name='risk_dashboard'),
]
