# payments/serializers.py
from rest_framework import serializers
from .models import Transaction
from users.serializers import UserSerializer

class TransactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Transaction
        fields = ['pk', 'user', 'amount', 'transaction_date', 'transaction_type']
        read_only_fields = ['pk', 'transaction_date']
