from django.urls import path
from .views import add_to_watch_history, create_vision, get_subscription_visions, get_trending_visions, get_visions_by_creator_category, upload_thumbnail, update_or_get_vision_info, get_recommended_visions, get_visions_by_creator, get_visions_by_interest, like_or_dislike_vision

urlpatterns = [
    path('create-vision/', create_vision, name='create_vision'),
    path('upload-thumbnail/<int:vision_pk>/', upload_thumbnail, name='upload_thumbnail'),
    path('vision-info/<int:vision_pk>/', update_or_get_vision_info, name='update_or_get_vision_info'),
    path('recommended-visions/', get_recommended_visions, name='get_recommended_visions'),
    path('visions-by-creator/<int:pk>/', get_visions_by_creator, name='get_visions_by_creator'),
    path('visions-by-interest/', get_visions_by_interest, name='get_visions_by_interest'),
    path('like-dislike-vision/<int:pk>/', like_or_dislike_vision, name='like_or_dislike_vision'),
    path('subscriptions/', get_subscription_visions, name='get_subscriptions'),
    path('trending/', get_trending_visions, name='get_trending_visions'),
    path('watch-history/add/', add_to_watch_history, name='add_to_watch_history'),
    path('visions-by-creator/<int:pk>/<str:category>/', get_visions_by_creator_category, name='get_visions_by_creator_category'),
    # path('nearby/', get_nearby_visions, name='get_nearby_visions'),
]
