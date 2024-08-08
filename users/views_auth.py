# users/views_auth.py
import json
import logging
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.authtoken.models import Token
from rest_framework import status
from http import HTTPStatus
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from videos.models import Vision
from .models import SignInCodeRequest, User, Spectator, Creator
from .serializers import CreatorSerializer, SpectatorSerializer
from django.db import IntegrityError
import os
import jwt
import requests
from django.utils import timezone
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from datetime import datetime, timedelta
from django.contrib.auth.models import BaseUserManager
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_creator_account(request):
    creator_instance = CreatorSerializer(data=request.data)
    user = User.objects.get(pk=request.user.pk)

    if creator_instance.is_valid():
        creator = Creator.objects.create(user=user, subscription_price=request.data['subscription_price'], subscriber_count=0)
        creator_account = CreatorSerializer(creator)

        return Response({"message": "Creator account created successfully", "data": creator_account.data}, status=status.HTTP_201_CREATED)
    else:
        return Response(creator_instance.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'DELETE'])
@permission_classes([AllowAny])
def creator_account_detail(request):
    if request.method == 'GET':
        try:
            creator_account = Creator.objects.get(user=request.user)
            creator_account_serializer = CreatorSerializer(creator_account)
            visions = Vision.with_locks.with_is_locked(request.user).filter(creator=creator_account)
            total_likes = sum(vision.likes for vision in visions)
            total_views = sum(vision.views for vision in visions)
            return Response({"data": creator_account_serializer.data, "stats": {"total_likes": total_likes, "total_views": total_views}}, status=HTTPStatus.OK)
        except Exception as e:
            return Response({"error": True, "message": f"The user with id {request.user.pk} has no creator account"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    elif request.method == 'DELETE':
        try:
            Creator.objects.filter(user=request.user).delete()
            return Response({"message": f"Successfully deleted creator account for user with id {request.user.pk}"}, status=HTTPStatus.OK)
        except:
            return Response({"error": True, "message": f"There was an error deleting creator account for user with id {request.user.pk}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_creator_accounts(request):
    if request.method == 'GET':
        accounts = Creator.objects.all()
        paginator = PageNumberPagination()
        paginator.page_size = 10
        results = paginator.paginate_queryset(accounts, request)
        return Response(CreatorSerializer(results, many=True).data)

@api_view(['POST'])
def create_spectator_account(request):
    spectator_account = SpectatorSerializer(data=request.data)
    if spectator_account.is_valid():
        spectator_account.save()
        return Response({"message": "Spectator account created successfully", "data": spectator_account.data}, status=status.HTTP_201_CREATED)
    else:
        return Response(spectator_account.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'DELETE'])
def spectator_account_detail(request):
    if request.method == 'GET':
        try:
            spectator_account = Spectator.objects.get(user=request.user)
            spectator_account_serializer = SpectatorSerializer(spectator_account)
            return Response({"data": spectator_account_serializer.data}, status=HTTPStatus.OK)
        except:
            return Response({"message": f"User with id {request.user.pk} does not have a spectator account"}, status=HTTPStatus.NOT_FOUND)
    elif request.method == 'DELETE':
        try:
            Spectator.objects.filter(user=request.user).delete()
            return Response({"message": f"Successfully deleted spectator account for user with id {request.user.pk}"}, status=HTTPStatus.OK)
        except:
            return Response({"message": f"There was an error deleting spectator account of user with id {request.user.pk}"}, status=HTTPStatus.BAD_REQUEST)

@api_view(['GET'])
def get_spectator_accounts(request):
    if request.method == 'GET':
        accounts = Spectator.objects.all()
        return Response(SpectatorSerializer(accounts, many=True).data)
    
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    username = request.data.get('username')
    email = request.data.get('email')
    first_name = request.data.get('firstname')
    last_name = request.data.get('lastname')
    password = request.data.get('password')
    password_confirmation = request.data.get('password_confirmation')

    print([username, email, first_name, last_name, password])

    # Check if all fields are provided
    if not all([username, email, first_name, last_name, password, password_confirmation]):
        return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if passwords match
    if password != password_confirmation:
        return Response({'error': 'Passwords do not match'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if email already exists
    if User.objects.filter(email=email).exists():
        return Response({'error': 'Email address already in use'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if username already exists
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password
        )

        # Create the associated Spectator account
        spectator = Spectator.objects.create(user=user)
        
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'user_id': user.id,
            'username': user.username,
            'profile_picture_url': user.profile_picture_url,
            'cover_picture_url': user.cover_picture_url,
            'is_spectator': user.is_spectator,
            'is_creator': user.is_creator,
            'sign_in_method': user.sign_in_method,
            'token': token.key
        }, status=status.HTTP_201_CREATED)
    except IntegrityError:
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(e)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
@permission_classes([AllowAny])
def sign_in(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)

    if user:
        token, _ = Token.objects.get_or_create(user=user)
        response_data = {
            'user_id': user.id,
            'username': user.username,
            'token': token.key,
        }
        # Optionally include other fields if they exist
        optional_fields = ['profile_picture_url', 'cover_picture_url', 'is_spectator', 'is_creator', 'sign_in_method']
        for field in optional_fields:
            response_data[field] = getattr(user, field, None)

        return Response(response_data)

    return Response({'error': 'Invalid Credentials'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def sign_in_google(request):
    try:
        google_token = request.data.get('credential')
        user_data = id_token.verify_oauth2_token(
            google_token, google_requests.Request(), os.environ['GOOGLE_OAUTH_CLIENT_ID']
        )
    except ValueError as e:
        print(e)
        return Response({"error": "Invalid Google token"}, status=status.HTTP_403_FORBIDDEN)

    email = user_data["email"]
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "username": email,
            "first_name": user_data.get("given_name"),
            "last_name": user_data.get("family_name"),
            "sign_in_method": 'google',
            "password": User.objects.make_random_password()
        }
    )

    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        'user_id': user.id,
        'username': user.username,
        'profile_picture_url': user.profile_picture_url,
        'cover_picture_url': user.cover_picture_url,
        'is_spectator': user.is_spectator,
        'is_creator': user.is_creator,
        'sign_in_method': user.sign_in_method,
        'email': user.email,
        'token': token.key
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def sign_in_facebook(request):
    FACEBOOK_DEBUG_TOKEN_URL = "https://graph.facebook.com/debug_token"
    FACEBOOK_ACCESS_TOKEN_URL = "https://graph.facebook.com/v7.0/oauth/access_token"
    FACEBOOK_URL = "https://graph.facebook.com/"

    access_token = request.data.get('access_token')
    
    if not access_token:
        return Response({"error": "Facebook access token is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Verify the access token
        app_id = os.environ.get("FACEBOOK_APP_ID")
        app_secret = os.environ.get("FACEBOOK_APP_SECRET")
        
        # Get app access token
        app_access_token_params = {
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "client_credentials",
        }
        app_access_token_response = requests.get(FACEBOOK_ACCESS_TOKEN_URL, params=app_access_token_params).json()
        app_access_token = app_access_token_response.get("access_token")

        if not app_access_token:
            return Response({"error": "Failed to get app access token"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Verify user access token
        verify_params = {
            "input_token": access_token,
            "access_token": app_access_token,
        }
        verify_response = requests.get(FACEBOOK_DEBUG_TOKEN_URL, params=verify_params).json()

        if "error" in verify_response or "data" not in verify_response:
            return Response({"error": "Invalid Facebook token"}, status=status.HTTP_403_FORBIDDEN)

        user_id = verify_response["data"]["user_id"]

        # Get user info
        user_info_params = {
            "fields": "id,name,email",
            "access_token": access_token,
        }
        user_info_response = requests.get(f"{FACEBOOK_URL}{user_id}", params=user_info_params).json()

        if "error" in user_info_response or "email" not in user_info_response:
            print(user_info_response)
            return Response({"error": "Failed to get user information"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        email = user_info_response["email"]
        
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email,
                "first_name": user_info_response.get("name", "").split()[0],
                "last_name": " ".join(user_info_response.get("name", "").split()[1:]),
                "sign_in_method": 'facebook',
                "password": User.objects.make_random_password()
            }
        )

        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            'user_id': user.id,
            'username': user.username,
            'profile_picture_url': user.profile_picture_url,
            'cover_picture_url': user.cover_picture_url,
            'is_spectator': user.is_spectator,
            'is_creator': user.is_creator,
            'sign_in_method': user.sign_in_method,
            'email': user.email,
            'token': token.key
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def sign_in_apple(request):
    ACCESS_TOKEN_URL = 'https://appleid.apple.com/auth/token'
    
    access_token = request.data.get('access_token')
    refresh_token = request.data.get('refresh_token')
    
    client_id, client_secret = get_apple_key_and_secret()
    
    headers = {'content-type': "application/x-www-form-urlencoded"}
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
    }
    
    if refresh_token is None:
        data['code'] = access_token
        data['grant_type'] = 'authorization_code'
    else:
        data['refresh_token'] = refresh_token
        data['grant_type'] = 'refresh_token'
    
    res = requests.post(ACCESS_TOKEN_URL, data=data, headers=headers)
    response_dict = res.json()
    
    if 'error' not in response_dict:
        id_token = response_dict.get('id_token', None)
        refresh_tk = response_dict.get('refresh_token', None)
        
        if id_token:
            decoded = jwt.decode(id_token, '', options={"verify_signature": False})
            email = decoded.get('email')
            
            if email:
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": email,
                        "first_name": email.split('@')[0],
                        "last_name": email.split('@')[0],
                        "sign_in_method": 'apple',
                        "password": User.objects.make_random_password()
                    }
                )
                
                token, _ = Token.objects.get_or_create(user=user)
                
                response_data = {
                    'user_id': user.id,
                    'username': user.username,
                    'profile_picture_url': user.profile_picture_url,
                    'cover_picture_url': user.cover_picture_url,
                    'is_spectator': user.is_spectator,
                    'is_creator': user.is_creator,
                    'sign_in_method': user.sign_in_method,
                    'email': user.email,
                    'token': token.key
                }
                
                if refresh_tk:
                    response_data['refresh_token'] = refresh_tk
                
                return Response(response_data, status=status.HTTP_200_OK)
            
    return Response({"error": "Invalid Apple token"}, status=status.HTTP_403_FORBIDDEN)

# Helper method
def get_apple_key_and_secret():
    AUTH_APPLE_KEY_ID = os.environ.get('AUTH_APPLE_KEY_ID')
    AUTH_APPLE_TEAM_ID = os.environ.get('AUTH_APPLE_TEAM_ID')
    AUTH_APPLE_CLIENT_ID = os.environ.get('AUTH_APPLE_CLIENT_ID')
    AUTH_APPLE_PRIVATE_KEY = os.environ.get('AUTH_APPLE_PRIVATE_KEY')

    headers = {
        'kid': AUTH_APPLE_KEY_ID,
        'alg': 'ES256'
    }
    payload = {
        'iss': AUTH_APPLE_TEAM_ID,
        'iat': timezone.now(),
        'exp': timezone.now() + timedelta(days=180),
        'aud': 'https://appleid.apple.com',
        'sub': AUTH_APPLE_CLIENT_ID,
    }
    client_secret = jwt.encode(
        payload, AUTH_APPLE_PRIVATE_KEY, algorithm="ES256", headers=headers
    )
    return AUTH_APPLE_CLIENT_ID, client_secret

@api_view(['GET'])
@permission_classes([AllowAny])
def check_signin_status(request):
    code = request.query_params.get('code')
    if not code:
        return Response({'error': 'Code is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        signin_request = SignInCodeRequest.objects.get(code=code)
        if signin_request.status == 'success':
            # Create or get the auth token
            user = User.objects.get(username=signin_request.user.username)
            token, _ = Token.objects.get_or_create(user=user)

            return Response({
                'status': 'success',
                'user_id': signin_request.user.pk,
                'username': signin_request.user.username,
                'auth_token': token.key  # Include the auth token in the response
            }, status=status.HTTP_200_OK)
        else:
            return Response({'status': 'pending'}, status=status.HTTP_200_OK)
    except SignInCodeRequest.DoesNotExist:
        return Response({'error': 'Invalid code'}, status=status.HTTP_404_NOT_FOUND)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def send_signin_code(request):
    if hasattr(request, 'data'):
        # This is a DRF request
        code = request.data.get('code')
    else:
        # This is a regular Django request
        try:
            data = json.loads(request.body)
            code = data.get('code')
        except json.JSONDecodeError:
            # If it's not JSON, try to get it from POST data
            code = request.POST.get('code')

    if not code:
        return Response({'error': 'Code is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Create or update the SignInCodeRequest
    signin_request = SignInCodeRequest.objects.create(
        code=code,
        status='pending'
    )

    return Response({'message': 'Sign-in code sent successfully'}, status=status.HTTP_200_OK)

