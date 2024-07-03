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

logger = logging.getLogger(__name__)

@api_view(['POST'])
def create_creator_account(request):
    creator_instance = CreatorSerializer(data=request.data)
    if creator_instance.is_valid():
        creator = Creator.objects.create(user=request.user, subscription_price=request.data['subscription_price'], subscriber_count=0)
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
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    password = request.data.get('password')

    if not all([username, email, first_name, last_name, password]):
        return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if email already exists
    if User.objects.filter(email=email).exists():
        return Response({'error': 'Email address already in use'}, status=status.HTTP_400_BAD_REQUEST)

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
            'token': token.key
        }, status=status.HTTP_201_CREATED)
    except IntegrityError:
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def sign_in(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'user_id': user.id,
            'username': user.username,
            'token': token.key
        })
    return Response({'error': 'Invalid Credentials'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def sign_in(request):
    email = request.data.get('email')
    password = request.data.get('password')
    
    try:
        # Get the user by email
        user = User.objects.get(email=email)
        
        # Authenticate using the username and password
        authenticated_user = authenticate(username=user.username, password=password)
        
        if authenticated_user:
            token, _ = Token.objects.get_or_create(user=authenticated_user)
            return Response({
                'user_id': authenticated_user.id,
                'username': authenticated_user.username,
                'email': authenticated_user.email,
                'token': token.key
            })
        else:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
    
    except User.DoesNotExist:
        return Response({'error': 'User with this email does not exist'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

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

