from django.urls import path
from .views import update_profile_picture, interest, add_or_remove_interest_from_spectator, search_interests, get_or_create_interests
from .views_auth import create_creator_account, creator_account_detail, get_creator_accounts, create_spectator_account, spectator_account_detail, get_spectator_accounts

urlpatterns = [
    path('update-profile-picture/', update_profile_picture, name='update_profile_picture'),
    path('interest/', interest, name='interest'),
    path('add-remove-interest/', add_or_remove_interest_from_spectator, name='add_or_remove_interest'),
    path('search-interests/', search_interests, name='search_interests'),
    path('get-create-interests/', get_or_create_interests, name='get_or_create_interests'),
    path('create-creator-account/', create_creator_account, name='create_creator_account'),
    path('creator-account/', creator_account_detail, name='creator_account_detail'),
    path('creator-accounts/', get_creator_accounts, name='get_creator_accounts'),
    path('create-spectator-account/', create_spectator_account, name='create_spectator_account'),
    path('spectator-account/', spectator_account_detail, name='spectator_account_detail'),
    path('spectator-accounts/', get_spectator_accounts, name='get_spectator_accounts'),
]
