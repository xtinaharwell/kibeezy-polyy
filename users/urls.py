from django.urls import path
from .views import signup_view, login_view, check_auth

urlpatterns = [
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('check/', check_auth, name='check_auth'),
]
