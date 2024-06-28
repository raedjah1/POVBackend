from django.urls import path
from .views import get_transactions, create_transaction

urlpatterns = [
    path('transactions/', get_transactions, name='get_transactions'),
    path('create-transaction/', create_transaction, name='create_transaction'),
]
