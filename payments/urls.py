from django.urls import path
from .views import initiate_stk_push, initiate_withdrawal, mpesa_callback, b2c_result_callback, test_mpesa_credentials, get_transaction_status, get_user_transactions

urlpatterns = [
    path('test-credentials/', test_mpesa_credentials, name='test_credentials'),
    path('stk-push/', initiate_stk_push, name='stk_push'),
    path('withdraw/', initiate_withdrawal, name='withdraw'),
    path('transaction/<int:transaction_id>/status/', get_transaction_status, name='transaction_status'),
    path('transactions/', get_user_transactions, name='user_transactions'),
    path('callback/', mpesa_callback, name='mpesa_callback'),
    path('b2c-callback/', b2c_result_callback, name='b2c_callback'),
]
