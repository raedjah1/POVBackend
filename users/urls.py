from django.urls import path
from .views import creator_live_status, get_all_badges, get_popular_creators, get_user_badges, search_creators, update_profile_picture, interest, add_or_remove_interest_from_spectator, search_interests, get_or_create_interests, update_user_details
from .views_auth import check_signin_status, create_creator_account, creator_account_detail, get_creator_accounts, create_spectator_account, register_user, send_signin_code, sign_in, sign_in_apple, sign_in_facebook, sign_in_google, spectator_account_detail, get_spectator_accounts

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
    path('popular-creators/', get_popular_creators, name='get_popular_creators'),
    path('auth/send-signin-code/', send_signin_code, name='send_signin_code'),
    path('auth/check-signin-status/', check_signin_status, name='check_signin_status'),
    path('register/', register_user, name='register'),
    path('sign-in/', sign_in, name='sign_in'),
    path('sign-in-google/', sign_in_google, name='sign_in_google'),
    path('sign-in-facebook/', sign_in_facebook, name='sign_in_facebook'),
    path('sign-in-apple/', sign_in_apple, name='sign_in_apple'),
    path('update-user-details/', update_user_details, name='update_user_details'),
    path('creator-live-status/<int:creator_id>/', creator_live_status, name='creator_live_status'),
    path('creators/search/', search_creators, name='search_creators'),
    path('badges/all/', get_all_badges, name='get_all_badges'),
    path('badges/user/', get_user_badges, name='get_user_badges'),
]
