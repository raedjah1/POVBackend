from django.urls import path
from .views import add_payment_method, get_payment_methods, get_transactions, create_transaction, send_tip, update_default_payment_method

urlpatterns = [
    path('transactions/', get_transactions, name='get_transactions'),
    path('create-transaction/', create_transaction, name='create_transaction'),
    path('send-tip/', send_tip, name='send_tip'),
    path('add_payment_method/', add_payment_method, name='add_payment_method'),
    path('get-payment-methods/', get_payment_methods, name='get_payment_methods'),
    path('update-default-payment-method/', update_default_payment_method, name='update_default_payment_method'),
]
