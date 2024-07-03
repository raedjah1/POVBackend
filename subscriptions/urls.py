from django.urls import path
from .views import check_subscription_status, get_subscribed_creators, subscribe, get_subscriptions, unsubscribe, update_creator_price

urlpatterns = [
    path('subscribe/<int:pk>/', subscribe, name='subscribe'),
    path('subscriptions/', get_subscriptions, name='get_subscriptions'),
    path('update-creator-price/', update_creator_price, name='update_creator_price'),
    path('subscribed-creators/', get_subscribed_creators, name='get_subscribed_creators'),
    path('subscription-status/<int:creator_id>/', check_subscription_status, name='check_subscription_status'),
    path('unsubscribe/<int:pk>/', unsubscribe, name='unsubscribe'),
]
