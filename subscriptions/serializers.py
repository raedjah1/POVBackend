# subscriptions/serializers.py
from rest_framework import serializers
from .models import Subscription, Promotion
from users.serializers import SpectatorSerializer, CreatorSerializer

class SubscriptionSerializer(serializers.ModelSerializer):
    spectator = SpectatorSerializer(read_only=True)
    creator = CreatorSerializer(read_only=True)
    
    class Meta:
        model = Subscription
        fields = ['pk', 'spectator', 'creator', 'start_date', 'end_date']
        read_only_fields = ['pk', 'start_date', 'end_date']

class PromotionSerializer(serializers.ModelSerializer):
    creator = CreatorSerializer(read_only=True)

    class Meta:
        model = Promotion
        fields = ['id', 'creator', 'stripe_coupon_id', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'stripe_coupon_id', 'created_at']