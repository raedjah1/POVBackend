from django.urls import path
from .views import subscribe, get_subscriptions

urlpatterns = [
    path('subscribe/<int:pk>/', subscribe, name='subscribe'),
    path('subscriptions/', get_subscriptions, name='get_subscriptions'),
]
