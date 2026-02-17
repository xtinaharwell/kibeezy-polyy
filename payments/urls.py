from django.urls import path
from .views import initiate_stk_push, mpesa_callback, b2c_result_callback, test_mpesa_credentials, get_transaction_status

urlpatterns = [
    path('test-credentials/', test_mpesa_credentials, name='test_credentials'),
    path('stk-push/', initiate_stk_push, name='stk_push'),
    path('transaction/<int:transaction_id>/status/', get_transaction_status, name='transaction_status'),
    path('callback/', mpesa_callback, name='mpesa_callback'),
    path('b2c-callback/', b2c_result_callback, name='b2c_callback'),
]
