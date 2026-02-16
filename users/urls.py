from django.urls import path
from .views import signup_view, login_view, check_auth, logout_view
from .kyc_views import start_kyc_verification, verify_kyc_otp, get_kyc_status

urlpatterns = [
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('check/', check_auth, name='check_auth'),
    path('kyc/start/', start_kyc_verification, name='start_kyc'),
    path('kyc/verify/', verify_kyc_otp, name='verify_kyc'),
    path('kyc/status/', get_kyc_status, name='kyc_status'),
]
