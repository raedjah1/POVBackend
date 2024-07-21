from django.urls import path
from .views import *

urlpatterns = [
    #path('create-vision/', create_vision, name='create_vision'),
    path('upload-thumbnail/<int:vision_pk>/', upload_thumbnail, name='upload_thumbnail'),
    path('vision-info/<int:vision_pk>/', update_or_get_vision_info, name='update_or_get_vision_info'),
    path('recommended-visions/', get_recommended_visions, name='get_recommended_visions'),
    path('visions-by-creator/<int:pk>/', get_visions_by_creator, name='get_visions_by_creator'),
    path('visions-by-interest/', get_visions_by_interest, name='get_visions_by_interest'),
    path('like-dislike-vision/<int:pk>/', like_or_dislike_vision, name='like_or_dislike_vision'),
    path('visions-from-subs/', get_recommended_visions_from_subs, name='get_recommended_visions_from_subs'),
    path('delete-vision/<int:pk>/', delete_vision, name='delete_vision'),
    path('search/', search_visions, name='search_visions'),

    path('watch_later/', get_watch_later, name='get_watch_later'),
    path('watch_later/add/<int:vision_pk>/', add_to_watch_later, name='add_to_watch_later'),
    path('watch_later/remove/<int:vision_pk>/', remove_from_watch_later, name='remove_from_watch_later'), 
    path('history/', get_watch_history, name='get_watch_history'), 
    path('history/add/<int:vision_pk>/', add_to_watch_history, name='add_to_watch_history'), 
    path('history/remove/<int:vision_pk>/', remove_from_watch_history, name= 'remove_from_watch_history'), 
    path('history/clear/', clear_watch_history, name='clear_watch_history'), 

    path('comment/<int:vision_id>/', get_comments, name='get_comments'), 
    path('comment/', post_comment, name='post_comment'), 
    path('comment/delete-like-dislike/<int:comment_id>/', delete_or_like_or_dislike_comment, name='delete_or_like_or_dislike_comment'), 
    

]
