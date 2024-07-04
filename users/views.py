# users/views.py

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from http import HTTPStatus
from django.db.models import Count
from .models import User, Interest, Spectator, Creator
from .serializers import InterestSerializer, UserSerializer, CreatorSerializer, SpectatorSerializer, RegistrationSerializer
import cloudinary.uploader


@api_view(['POST'])
def update_profile_picture(request):
    try:
        user = User.objects.get(pk=request.user.pk)
        profile_picture = request.FILES['profile_picture']
        res = cloudinary.uploader.upload(profile_picture, public_id=f'profile_picture_{request.user.username}', overwrite=True, unique_filename=True)
        user.profile_picture_url = res['secure_url']
        user.save()
        return Response({'message': 'Profile picture updated successfully', 'profile_picture': user.profile_picture_url})
    except Exception as e:
        return Response({'error': True, 'message': 'There was an error'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def interest(request):
    try:
        paginator = PageNumberPagination()
        paginator.page_size = 20
        interests = Interest.objects.all()
        results = paginator.paginate_queryset(interests, request)
        return Response({
            'data': InterestSerializer(results, many=True).data,
            'size': len(interests),
            'next': paginator.get_next_link(),
            'prev': paginator.get_previous_link()
        })
    except Exception as e:
        return Response({'error': True, 'message': 'There was an error'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def add_or_remove_interest_from_spectator(request):
    try:
        user = User.objects.get(pk=request.user.pk)
        spectator = user.spectator
        spectator.interests.clear()
        for interest_name in request.data['interests']:
            interest = Interest.objects.get(name=interest_name)
            spectator.interests.add(interest)
        spectator.save()
        return Response({'message': 'Interests added to spectator successfully!'})
    except Exception as e:
        return Response({'error': True, 'message': 'There was an error'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_interests(request):
    try:
        query = request.GET.get('name', '')
        interests = Interest.objects.filter(name__icontains=query)
        return Response({
            'message': 'Interest found',
            'data': InterestSerializer(interests, many=True).data
        }, status=HTTPStatus.OK)
    except Exception as e:
        return Response({'message': str(e), 'error': True}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def get_or_create_interests(request):
    try:
        interests = request.data['interests']
        for interest_name in interests:
            Interest.objects.get_or_create(name=interest_name)
        interest_data = Interest.objects.filter(name__in=interests)
        return Response({'interests': InterestSerializer(interest_data, many=True).data})
    except Exception as e:
        return Response({'error': True, 'message': 'There was an error'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes((AllowAny,))
def register(request):
    try:
        registered_user = RegistrationSerializer(data=request.data)
        if registered_user.is_valid():
            instance = registered_user.save()
            instance.set_password(request.data.get('password'))
            instance.save()

            token = Token.objects.create(user=instance)
            serialized_user = UserSerializer(instance)

            Spectator.objects.create(user=instance)
            Creator.objects.create(user=instance, subscription_price=0, subscriber_count=0)

            return Response({
                'token': token.key,
                'message': 'Registration successful!',
                'user': serialized_user.data
            })
        else:
            return Response(registered_user.errors, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return Response({
            "error": True,
            "message": "There was an error"
        }, status=HTTPStatus.INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes((AllowAny,))
def login(request):
    try:
        username = request.data.get('username')
        password = request.data.get('password')

        if username is None or password is None:
            return Response({
                'message': 'Please provide both username and password',
                'status': HTTPStatus.BAD_REQUEST,
                'error': True
            })

        user = authenticate(username=username, password=password)

        if not user:
            return Response({
                'message': 'Incorrect Username or Password',
                'status': HTTPStatus.NOT_FOUND,
                'error': True
            })

        token, _ = Token.objects.get_or_create(user=user)
        serialized_user = UserSerializer(user)

        return Response({
            'token': token.key,
            'message': 'Log in successful!',
            'user': serialized_user.data
        })
    except Exception as e:
        return Response({
            'message': 'There was an error! Please try again',
            'error': True
        }, status=HTTPStatus.INTERNAL_SERVER_ERROR)
