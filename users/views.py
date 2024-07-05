# users/views.py
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from http import HTTPStatus
from .models import User, Interest, Creator
from .serializers import InterestSerializer, CreatorSerializer, UserSerializer
import cloudinary.uploader
from django.db.models import Sum, F, ExpressionWrapper, FloatField
from django.db.models.functions import Coalesce
from rest_framework.authentication import TokenAuthentication
from rest_framework import status

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
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

@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_user_details(request):
    user = User.objects.get(pk=request.user.pk)
    
    # Get the data from the request
    username = request.data.get('username')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')

    # Update the fields if they are provided
    if username:
        # Check if the username is already taken
        if User.objects.filter(username=username).exclude(id=user.id).exists():
            return Response({"error": "This username is already taken."}, status=status.HTTP_400_BAD_REQUEST)
        user.username = username

    if first_name:
        user.first_name = first_name

    if last_name:
        user.last_name = last_name

    try:
        user.save()
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
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
        interests = Interest.objects.filter(name__icontains=query) #TODO Fuzzy Search
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

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_popular_creators(request):
    
    # Calculate the weighted score for each creator
    popular_creators = Creator.objects.annotate(
        total_views=Coalesce(Sum('vision__views'), 0),
        total_likes=Coalesce(Sum('vision__likes'), 0),
        weighted_score=ExpressionWrapper(
            (F('total_views') * 1) +  # Weight for views
            (F('total_likes') * 3) +  # Weight for likes
            (F('subscriber_count') * 5),  # Weight for subscribers
            output_field=FloatField()
        )
    ).order_by('-weighted_score')

    paginator = PageNumberPagination()
    paginator.page_size = 10
    results = paginator.paginate_queryset(popular_creators, request)

    serializer = CreatorSerializer(results, many=True)
    return paginator.get_paginated_response(serializer.data)
