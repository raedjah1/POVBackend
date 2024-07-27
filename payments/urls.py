from django.urls import path
from .views import get_transactions, create_transaction, send_tip

urlpatterns = [
    path('transactions/', get_transactions, name='get_transactions'),
    path('create-transaction/', create_transaction, name='create_transaction'),
    path('send-tip/', send_tip, name='send_tip'),
]
