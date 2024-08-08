# users/views.py
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from http import HTTPStatus
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from videos.models import Vision
from videos.serializers import VisionSerializer
from .models import User, Interest, Creator, Badge, UserBadge
from .serializers import BadgeSerializer, UserBadgeSerializer, InterestSerializer, CreatorSerializer, UserSerializer
import cloudinary.uploader
from django.db.models import Sum, F, ExpressionWrapper, FloatField
from django.db.models.functions import Coalesce
from rest_framework.authentication import TokenAuthentication
from rest_framework import status
from django.contrib.postgres.search import TrigramSimilarity
from rest_framework.response import Response

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
        print("Received headers:", request.headers)
        print("User authenticated:", request.user.is_authenticated)
        print("Authenticated user:", request.user)

        add_interests = request.data.get('add_interests', [])
        remove_interests = request.data.get('remove_interests', [])

        user = User.objects.get(pk=request.user.pk)
        spectator = user.spectator

        # Remove specified interests
        for interest_name in remove_interests:
            try:
                interest = Interest.objects.get(name=interest_name)
                spectator.interests.remove(interest)
                print(f"Removed interest {interest_name} from user {user.pk}")
            except Interest.DoesNotExist:
                print(f"Interest '{interest_name}' does not exist")
                return Response({'error': True, 'message': f'Interest "{interest_name}" does not exist'}, status=status.HTTP_400_BAD_REQUEST)

        # Add specified interests
        for interest_name in add_interests:
            try:
                interest = Interest.objects.get(name=interest_name)
                spectator.interests.add(interest)
                print(f"Added interest {interest_name} to user {user.pk}")
            except Interest.DoesNotExist:
                print(f"Interest '{interest_name}' does not exist")
                return Response({'error': True, 'message': f'Interest "{interest_name}" does not exist'}, status=status.HTTP_400_BAD_REQUEST)

        spectator.save()
        return Response({'message': 'Interests updated successfully!'})
    except Exception as e:
        print("Error:", str(e))
        return Response({'error': True, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def search_interests(request):
    try:
        query = request.data.get('search_text', '')

        if not query:
            return Response({
                'message': 'Please provide a search query',
                'error': True
            }, status=status.HTTP_400_BAD_REQUEST)

        interests = Interest.objects.annotate(
            similarity=TrigramSimilarity('name', query)
        ).filter(similarity__gt=0.3).order_by('-similarity')

        return Response({
            'message': 'Interests found',
            'data': InterestSerializer(interests, many=True).data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'message': str(e), 'error': True}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_or_create_interests(request):
    try:
        interests = request.data.get('interests', [])
        
        if not interests:
            return Response({'error': True, 'message': 'No interests provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        interest_objects = []
        for interest_name in interests:
            interest, created = Interest.objects.get_or_create(name=interest_name)
            interest_objects.append({
                'id': interest.id,
                'name': interest.name,
                'created': created
            })

        return Response({
            'interests': interest_objects
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': True, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

@api_view(['GET'])
def creator_live_status(request, creator_id):
    try:
        creator = Creator.objects.get(pk=creator_id)
        
        # Get the creator's live vision (assuming only one can be live at a time)
        live_vision = Vision.objects.filter(creator=creator, live=True).first()
        
        status_data = {
            'is_live': live_vision is not None,
            'creator_id': creator_id,
            'vision': VisionSerializer(live_vision).data if live_vision else None
        }
        
        return Response(status_data)
    except Creator.DoesNotExist:
        return Response({'error': 'Creator not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def search_creators(request):
    try:
        search_text = request.data.get('search_text', '')
        interest_name = request.data.get('interest')

        # Create the search vector
        search_vector = SearchVector('user__username', weight='A') + \
                        SearchVector('bio', weight='B') + \
                        SearchVector('user__interests__name', weight='C')

        # Create the search query
        search_query = SearchQuery(search_text)

        # Filter and rank the results
        creators = Creator.objects.annotate(
            rank=SearchRank(search_vector, search_query)
        ).filter(rank__gte=0.01).order_by('-rank')

        # Apply interest filter if provided
        if interest_name:
            try:
                interest = Interest.objects.get(name=interest_name)
                creators = creators.filter(user__interests=interest)
            except Interest.DoesNotExist:
                return Response({'error': 'Interest not found'}, status=status.HTTP_404_NOT_FOUND)

        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 10  # Set the number of items per page
        result_page = paginator.paginate_queryset(creators, request)

        serializer = CreatorSerializer(result_page, many=True)

        return paginator.get_paginated_response(serializer.data)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_badges(request):
    badges = Badge.objects.all()
    serializer = BadgeSerializer(badges, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_badges(request):
    user_badges = UserBadge.objects.filter(user=request.user)
    serializer = UserBadgeSerializer(user_badges, many=True)
    return Response(serializer.data)

# @api_view(['GET'])
# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
# def phone_connection_status(request):
#     try:
#         # Refresh the user object from the database
#         user = User.objects.get(pk=request.user.pk)
#         status_data = {
#             'is_connected': user.phone_connected
#         }

#         return Response(status_data)
#     except User.DoesNotExist:
#         return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
#     except Exception as e:
#         return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    