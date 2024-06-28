from django.urls import path
from .views import create_vision, upload_thumbnail, update_or_get_vision_info, get_recommended_visions, get_visions_by_creator, get_visions_by_interest, like_or_dislike_vision

urlpatterns = [
    path('create-vision/', create_vision, name='create_vision'),
    path('upload-thumbnail/<int:vision_pk>/', upload_thumbnail, name='upload_thumbnail'),
    path('vision-info/<int:vision_pk>/', update_or_get_vision_info, name='update_or_get_vision_info'),
    path('recommended-visions/', get_recommended_visions, name='get_recommended_visions'),
    path('visions-by-creator/<int:pk>/', get_visions_by_creator, name='get_visions_by_creator'),
    path('visions-by-interest/', get_visions_by_interest, name='get_visions_by_interest'),
    path('like-dislike-vision/<int:pk>/', like_or_dislike_vision, name='like_or_dislike_vision'),
]
