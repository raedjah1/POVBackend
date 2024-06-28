# subscriptions/serializers.py
from rest_framework import serializers
from .models import Subscription
from users.serializers import SpectatorSerializer, CreatorSerializer

class SubscriptionSerializer(serializers.ModelSerializer):
    spectator = SpectatorSerializer(read_only=True)
    creator = CreatorSerializer(read_only=True)
    
    class Meta:
        model = Subscription
        fields = ['pk', 'spectator', 'creator', 'start_date', 'end_date']
        read_only_fields = ['pk', 'start_date', 'end_date']
