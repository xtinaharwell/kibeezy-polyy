from django.urls import path
from .views import initiate_stk_push, mpesa_callback, b2c_result_callback

urlpatterns = [
    path('stk-push/', initiate_stk_push, name='stk_push'),
    path('callback/', mpesa_callback, name='mpesa_callback'),
    path('b2c-callback/', b2c_result_callback, name='b2c_callback'),
]
