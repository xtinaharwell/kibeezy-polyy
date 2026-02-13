from django.urls import path
from .views import list_markets, place_bet

urlpatterns = [
    path('', list_markets, name='list_markets'),
    path('bet/', place_bet, name='place_bet'),
]
