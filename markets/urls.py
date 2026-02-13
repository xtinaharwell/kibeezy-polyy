from django.urls import path
from .views import list_markets, place_bet
from .dashboard_views import user_dashboard, transaction_history, initiate_withdrawal
from .admin_views import admin_markets, resolve_market, create_market

urlpatterns = [
    path('', list_markets, name='list_markets'),
    path('bet/', place_bet, name='place_bet'),
    
    # Dashboard endpoints
    path('dashboard/', user_dashboard, name='user_dashboard'),
    path('history/', transaction_history, name='transaction_history'),
    path('withdraw/', initiate_withdrawal, name='initiate_withdrawal'),
    
    # Admin endpoints
    path('admin/markets/', admin_markets, name='admin_markets'),
    path('admin/resolve/', resolve_market, name='resolve_market'),
    path('admin/create/', create_market, name='create_market'),
]
