import logging
import re
import cloudinary.uploader
import boto3
from botocore.client import Config
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from http import HTTPStatus
from django.db.models import Q
from .models import Vision, Comment
from .serializers import CommentSerializer, VisionSerializer
from users.models import Interest, Spectator, Creator
import os
from django.db.models import Count, Q, F, ExpressionWrapper, FloatField, Case, When, Value
from django.db.models.functions import Cast
from django.db.models.functions import Cast
from django.utils import timezone
from datetime import timedelta
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import Vision, Poll, PollItem, Vote
from .serializers import PollSerializer, PollItemSerializer
from firebase_admin import firestore, credentials
import json

try:
    # Parse the JSON string from the config var if it exists
    google_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if google_creds:
        cred_dict = json.loads(google_creds)

        # Initialize Firebase Admin SDK
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    else:
        print("GOOGLE_APPLICATION_CREDENTIALS environment variable not found.")
except Exception as e:
    print(f"An error occurred while initializing Firebase: {str(e)}")    

# TODO Nearby Vision, GDAL library
# from django.contrib.gis.geos import Point
# from django.contrib.gis.db.models.functions import Distance
# from django.contrib.gis.measure import D

logger = logging.getLogger(__name__)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_vision(request):
    try:
        vision_obj = VisionSerializer(data=request.data)
        if vision_obj.is_valid():
            vision_instance = vision_obj.save()
            vision_instance.creator = Creator.objects.get(user=request.user)
            
            s3 = boto3.client('s3', config=Config(signature_version='s3v4', region_name='us-east-2'))
            filename = f'{request.user.username}-{vision_obj.validated_data["title"].replace(" ", "")}-vision-{vision_instance.pk}.mp4'
            presigned_post = s3.generate_presigned_post(Bucket=os.environ.get('S3_BUCKET'), Key=filename, Fields={"acl": "public-read", "Content-Type": "video/mp4"}, Conditions=[{"acl": "public-read"}], ExpiresIn=36000)
            vision_instance.url = f'https://{os.environ.get("CLOUDFRONT_DOMAIN")}/{filename}'
            vision_instance.save()
            return Response({'data': presigned_post, 'url': f'https://{os.environ.get("S3_BUCKET")}.s3.amazonaws.com/{filename}', 'id': vision_instance.pk})
        else:
            return Response({'message': 'There was an error', 'error': vision_obj.errors}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error creating vision: {e}")
        return Response({'error': True, 'message': 'There was an error'}, status=HTTPStatus.BAD_REQUEST)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_live_vision(request):
    try:
        vision_obj = VisionSerializer(data=request.data)
        if vision_obj.is_valid():
            vision_instance = vision_obj.save()
            vision_instance.creator = Creator.objects.get(user=request.user)
            vision_instance.is_live = True
            
            # Set the URL for HLS playback
            vision_instance.url = f'{settings.FILE_HOST}/{vision_instance.pk}.m3u8'
            
            # Get thumbnail upload
            thumbnail = request.FILES.get('thumbnail')
            if thumbnail:
                thumbnail = request.FILES['thumbnail']
                thumbnail_res = cloudinary.uploader.upload(thumbnail, public_id=f'{request.user.username}-{vision_instance.pk}-thumbnail', unique_filename=False, overwrite=True)
                vision_instance.thumbnail = thumbnail_res['secure_url']
            
            vision_instance.save()

            # Generate RTMP stream link
            rtmp_stream_link = f'{settings.RTMP_HOST}/stream/{vision_instance.pk}'
            return Response({
                'message': 'Successfully created live vision',
                'vision_id': vision_instance.pk,
                'hls_url': vision_instance.url,
                'rtmp_stream_link': rtmp_stream_link
            })
        else:
            return Response({'message': 'There was an error', 'error': vision_obj.errors}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error creating live vision: {e}")
        return Response({'error': True, 'message': 'There was an error creating live vision'}, status=HTTPStatus.BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([AllowAny])
def end_live_vision(request, vision_pk):
    api_key = request.GET.get('api_key')

    if api_key != settings.NGINX_API_KEY:
        return Response({"error": "Unauthorized"}, status=401)
    
    try:
        vision = Vision.with_locks.with_is_locked(request.user).get(pk=vision_pk)

        if vision.is_live:
            vision.is_live = False
            
            # Get manifest file from B2 bucket
            b2_client = boto3.client('b2')
            manifest_file_key = f'{vision_pk}.m3u8'
            manifest_file_obj = b2_client.get_object(Bucket=os.environ.get('B2_BUCKET'), Key=manifest_file_key)
            manifest_content = manifest_file_obj['Body'].read().decode('utf-8')
            
            # Check if #EXT-X-PLAYLIST-TYPE already exists
            playlist_type_pattern = re.compile(r'#EXT-X-PLAYLIST-TYPE:.*\n')
            if playlist_type_pattern.search(manifest_content):
                # Replace existing playlist type with VOD
                manifest_content = playlist_type_pattern.sub('#EXT-X-PLAYLIST-TYPE:VOD\n', manifest_content)
            else:
                # Add VOD playlist type near the beginning (after #EXTM3U)
                manifest_content = manifest_content.replace('#EXTM3U\n', '#EXTM3U\n#EXT-X-PLAYLIST-TYPE:VOD\n', 1)

            # Ensure #EXT-X-ENDLIST is at the end
            if '#EXT-X-ENDLIST' not in manifest_content:
                manifest_content += '\n#EXT-X-ENDLIST'
            
            # Put updated manifest back to B2
            b2_client.put_object(Bucket=os.environ.get('B2_BUCKET'), Key=manifest_file_key, Body=manifest_content.encode('utf-8'))
            
            vision.save()
            return Response({'message': 'Successfully ended live vision'})
        else:
            return Response({'message': 'Vision is not live'}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error ending live vision: {e}")
        return Response({'error': True, 'message': 'There was an error ending live vision'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def upload_thumbnail(request, vision_pk):
    try:
        vision = Vision.with_locks.with_is_locked(request.user).get(pk=vision_pk)
        thumbnail = request.FILES['thumbnail']
        thumbnail_res = cloudinary.uploader.upload(thumbnail, public_id=f'{request.user.username}-{vision.pk}-thumbnail', unique_filename=False, overwrite=True)
        vision.thumbnail = thumbnail_res['secure_url']
        vision.save()
        return Response({'message': 'Successfully uploaded thumbnail'})
    except Exception as e:
        logger.error(f"Error uploading thumbnail: {e}")
        return Response({'error': True, 'message': 'There was an error'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['PUT', 'GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_or_get_vision_info(request, vision_pk):
    if request.method == 'GET':
        try:
            vision = Vision.with_locks.with_is_locked(request.user).get(pk=vision_pk)
            return Response({'message': 'Successfully retrieved vision', 'data': VisionSerializer(vision).data})
        except Vision.DoesNotExist:
            return Response({'error': True, 'message': 'Vision not found'}, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving vision info: {e}")
            return Response({'error': True, 'message': 'There was an error'}, status=HTTPStatus.BAD_REQUEST)
    elif request.method == 'PUT':
        try:
            vision = Vision.with_locks.with_is_locked(request.user).get(pk=vision_pk)

            # Check if thumbnail is included in the request
            if 'thumbnail' in request.FILES:
                thumbnail = request.FILES['thumbnail']
                thumbnail_res = cloudinary.uploader.upload(thumbnail, public_id=f'{request.user.username}-{vision.pk}-thumbnail', unique_filename=False, overwrite=True)
                vision.thumbnail = thumbnail_res['secure_url']

            new_info = VisionSerializer(vision, data=request.data, partial=True)
            
            if new_info.is_valid():
                new_info.save()
                return Response({'message': 'Successfully updated vision', 'data': new_info.data})
            else:
                return Response({'message': 'There was an error', 'error': new_info.errors}, status=HTTPStatus.BAD_REQUEST)
        except Vision.DoesNotExist:
            return Response({'error': True, 'message': 'Vision not found'}, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating vision info: {e}")
            return Response({'error': True, 'message': 'There was an error'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_recommended_visions(request):
    try:
        paginator = PageNumberPagination()
        paginator.page_size = 10

        # Simple Recommendations:
        # user_interests = Spectator.objects.get(user=request.user).interests.all()
        # if not user_interests.exists():
        #     visions = Vision.with_locks.with_is_locked(request.user).filter(~Q(url=None)).order_by('-created_at', '-likes')
        # else:
        #     visions = Vision.with_locks.with_is_locked(request.user).filter(interests__in=user_interests).filter(~Q(url=None)).distinct().order_by('-created_at', '-likes')

        visions = get_recommended_visions_algorithm(request.user)
        results = paginator.paginate_queryset(visions, request)
        return paginator.get_paginated_response(VisionSerializer(results, many=True).data)
    except Exception as e:
        logger.error(f"Error fetching recommended visions: {e}")
        return Response({'error': True}, status=HTTPStatus.BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_visions_by_creator(request, pk):
    try:
        creator = Creator.objects.get(pk=pk)
        visions = Vision.with_locks.with_is_locked(request.user).filter(creator=creator).order_by('-created_at')
        paginator = PageNumberPagination()
        paginator.page_size = 10
        results = paginator.paginate_queryset(visions, request)
        return paginator.get_paginated_response(VisionSerializer(results, many=True).data)
    except Exception as e:
        logger.error(f"Error fetching visions by creator: {e}")
        return Response({'error': True}, status=HTTPStatus.BAD_REQUEST)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_visions_by_interest(request):
    try:
        interests = [Interest.objects.get(name=interest_name) for interest_name in request.data['interests']]
        visions = Vision.with_locks.with_is_locked(request.user).filter(interests__in=interests).filter(~Q(url=None)).distinct().order_by('-created_at', '-likes')
        paginator = PageNumberPagination()
        paginator.page_size = 10
        results = paginator.paginate_queryset(visions, request)
        return paginator.get_paginated_response(VisionSerializer(results, many=True).data)
    except Exception as e:
        logger.error(f"Error fetching visions by interest: {e}")
        return Response({'error': True}, status=HTTPStatus.BAD_REQUEST)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def like_or_dislike_vision(request, pk):
    try:
        vision = Vision.with_locks.with_is_locked(request.user).get(pk=pk)
        spectator = Spectator.objects.get(user=request.user)
        if vision in spectator.liked_visions.all():
            vision.likes = max(vision.likes - 1, 0)
            spectator.liked_visions.remove(vision)
            message = 'Vision disliked'
        else:
            vision.likes += 1
            spectator.liked_visions.add(vision)
            message = 'Vision liked'
        vision.save()
        return Response({'message': message})
    except Exception as e:
        logger.error(f"Error liking/disliking vision: {e}")
        return Response({'error': True}, status=HTTPStatus.BAD_REQUEST)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_to_watch_history(request):
    vision_id = request.data.get('vision_id')
    try:
        vision = Vision.with_locks.with_is_locked(request.user).get(pk=vision_id)
        
        spectator = Spectator.objects.get(user=request.user)
        spectator.watch_history.add(vision)

        # Optional: Limit history to last x videos
        # if spectator.watch_history.count() > 100000:
        #     oldest = spectator.watch_history.order_by('watch_history__id').first()
        #     spectator.watch_history.remove(oldest)

        return Response({'message': 'Added to watch history'}, status=status.HTTP_200_OK)
    except Vision.DoesNotExist:
        return Response({'error': 'Vision not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_subscription_visions(request):
    spectator = Spectator.objects.get(user=request.user)
    subscribed_visions = Vision.with_locks.with_is_locked(request.user).filter(creator__in=spectator.subscriptions.all()).order_by('-created_at')
    
    paginator = PageNumberPagination()
    paginator.page_size = 10
    page = paginator.paginate_queryset(subscribed_visions, request)
    
    if page is not None:
        serializer = VisionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    return Response(None)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_trending_visions(request):
    # Get visions from the last month
    one_month_ago = timezone.now() - timedelta(days=30)

    trending_visions = Vision.with_locks.with_is_locked(request.user).filter(created_at__gte=one_month_ago)
    
    # Calculate weighted score
    trending_visions = trending_visions.annotate(
        comment_count=Count('comment')
    ).annotate(
        weighted_score=ExpressionWrapper(
            (Cast('likes', FloatField()) * 3) +  # Likes have a weight of 3
            (Cast('comment_count', FloatField()) * 2) +  # Comments have a weight of 2
            Cast('views', FloatField()),  # Views have a weight of 1
            output_field=FloatField()
        )
    ).order_by('-weighted_score')

    paginator = PageNumberPagination()
    paginator.page_size = 10
    page = paginator.paginate_queryset(trending_visions, request)

    if page is not None:
        serializer = VisionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    return Response(None)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_visions_by_creator_category(request, pk, category):
    try:
        creator = Creator.objects.get(pk=pk)
        
        if category == 'saved':
            visions = Vision.with_locks.with_is_locked(request.user).filter(creator=creator, is_saved=True)
        elif category == 'highlights':
            visions = Vision.with_locks.with_is_locked(request.user).filter(creator=creator, is_highlight=True)
        elif category == 'forme':
            if request.user.is_authenticated:
                visions = Vision.with_locks.with_is_locked(request.user).filter(creator=creator, private_user=request.user)
            else:
                visions = Vision.with_locks.with_is_locked(request.user).filter(creator=creator)
        else:
            return Response({'error': 'Invalid category'}, status=HTTPStatus.BAD_REQUEST)
        
        visions = visions.order_by('-created_at')
        
        paginator = PageNumberPagination()
        paginator.page_size = 10
        results = paginator.paginate_queryset(visions, request)
        return paginator.get_paginated_response(VisionSerializer(results, many=True).data)
    except Creator.DoesNotExist:
        return Response({'error': 'Creator not found'}, status=HTTPStatus.NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=HTTPStatus.BAD_REQUEST)

def get_recommended_visions_algorithm(user):
    spectator = Spectator.objects.get(user=user)
    
    # Base queryset
    base_queryset = Vision.with_locks.with_is_locked(user)
    
    # User's interests and watch history
    user_interests = spectator.interests.all()
    watch_history = spectator.watch_history.all()
    creators_watched = watch_history.values_list('creator', flat=True).distinct()
    
    # Collaborative Filtering
    liked_visions = spectator.liked_visions.all()
    similar_users = Spectator.objects.filter(liked_visions__in=liked_visions).distinct().exclude(user=user)
    
    # Trending Content timeframe
    one_month_ago = timezone.now() - timedelta(days=30)
    
    recommended = base_queryset.annotate(
        # Content-Based Scoring
        interest_match=Count('interests', filter=Q(interests__in=user_interests)),
        
        # Collaborative Scoring
        similar_user_likes=Count('liked_by', filter=Q(liked_by__in=similar_users)),
        
        # History-Based Scoring
        creator_watched=Case(
            When(creator__in=creators_watched, then=Value(1)),
            default=Value(0),
            output_field=FloatField()
        ),
        
        # Recency and Popularity Scoring
        comment_count=Count('comment'),
        recency_score=Case(
            When(created_at__gte=one_month_ago, then=Value(1)),
            default=Value(0),
            output_field=FloatField()
        )
    ).exclude(
        pk__in=watch_history.values_list('pk', flat=True)
    ).annotate(
        relevance_score=ExpressionWrapper(
            (F('interest_match') * 3) +  # Prioritize content matching user interests
            (F('similar_user_likes') * 2) +  # Consider similar users' preferences
            (F('creator_watched') * 1.5) +  # Slight boost for creators user has watched before
            (F('likes') * 0.5) +  # Consider overall popularity
            (F('comment_count') * 0.3) +  # Engagement factor
            (F('views') * 0.1) +  # View count as a minor factor
            (F('recency_score') * 5),  # Boost for recent content
            output_field=FloatField()
        )
    ).order_by('-relevance_score')
    
    return recommended

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def like_comment(request, comment_pk):
    try:
        comment = Comment.objects.get(pk=comment_pk)
        user = request.user
        
        if user not in comment.likes.all():
            comment.likes.add(user)
            return Response({'message': 'Comment liked successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Comment already liked'}, status=status.HTTP_200_OK)
    
    except Comment.DoesNotExist:
        return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def unlike_comment(request, comment_pk):
    try:
        comment = Comment.objects.get(pk=comment_pk)
        user = request.user
        
        if user in comment.likes.all():
            comment.likes.remove(user)
            return Response({'message': 'Comment unliked successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Comment was not liked'}, status=status.HTTP_200_OK)
    
    except Comment.DoesNotExist:
        return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def search_visions(request):
    try:
        search_text = request.data.get('search_text', '')
        interest_name = request.data.get('interest')

        # Create the search vector
        search_vector = SearchVector('title', weight='A') + \
                        SearchVector('description', weight='B') + \
                        SearchVector('interests__name', weight='C')

        # Create the search query
        search_query = SearchQuery(search_text)

        # Filter and rank the results
        visions = Vision.objects.annotate(
            rank=SearchRank(search_vector, search_query)
        ).filter(rank__gte=0.01).order_by('-rank')

        # Apply interest filter if provided
        if interest_name:
            try:
                interest = Interest.objects.get(name=interest_name)
                visions = visions.filter(interests=interest)
            except Interest.DoesNotExist:
                return Response({'error': 'Interest not found'}, status=status.HTTP_404_NOT_FOUND)

        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 10  # Set the number of items per page
        result_page = paginator.paginate_queryset(visions, request)

        serializer = VisionSerializer(result_page, many=True)

        return paginator.get_paginated_response(serializer.data)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_vision_comments(request, vision_id):
    try:
        # Check if the vision exists
        vision = Vision.objects.get(pk=vision_id)
        
        # Get all comments for this vision
        comments = Comment.objects.filter(vision=vision).order_by('-created_at')
        
        # Set up pagination
        paginator = PageNumberPagination()
        paginator.page_size = 10  # You can adjust this number as needed
        
        # Paginate the results
        paginated_comments = paginator.paginate_queryset(comments, request)
        
        # Serialize the paginated comments
        serializer = CommentSerializer(paginated_comments, many=True, context={'request': request})
        
        # Return the paginated response
        return paginator.get_paginated_response(serializer.data)
    
    except Vision.DoesNotExist:
        return Response({'error': 'Vision not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_comment_replies(request, comment_id):
    try:
        # Check if the parent comment exists
        parent_comment = Comment.objects.get(pk=comment_id)
        
        # Get all replies for this comment
        replies = Comment.objects.filter(parent_comment=parent_comment).order_by('created_at')
        
        # Set up pagination
        paginator = PageNumberPagination()
        paginator.page_size = 10  # You can adjust this number as needed
        
        # Paginate the results
        paginated_replies = paginator.paginate_queryset(replies, request)
        
        # Serialize the paginated replies
        serializer = CommentSerializer(paginated_replies, many=True, context={'request': request})
        
        # Return the paginated response
        return paginator.get_paginated_response(serializer.data)
    
    except Comment.DoesNotExist:
        return Response({'error': 'Parent comment not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_poll(request):
    vision_id = request.data.get('vision_id')
    try:
        vision = Vision.objects.get(id=vision_id)
    except Vision.DoesNotExist:
        return Response({"error": "Vision not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = PollSerializer(data=request.data)
    if serializer.is_valid():
        poll = serializer.save(vision=vision)
        
        # Write to Firestore
        db = firestore.client()
        db.collection('active_polls').document(str(poll.id)).set({
            'poll_id': poll.id,
            'question': poll.question,
            'items': [{'id': item.id, 'text': item.text, 'votes': 0} for item in poll.items.all()],
            'total_votes': 0,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_poll_details(request, poll_id):
    try:
        poll = Poll.objects.get(id=poll_id)
        serializer = PollSerializer(poll)
        return Response(serializer.data)
    except Poll.DoesNotExist:
        return Response({"error": "Poll not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@transaction.atomic
def submit_poll_vote(request):
    poll_item_id = request.data.get('poll_item_id')
    user = request.user

    try:
        poll_item = PollItem.objects.select_related('poll').get(id=poll_item_id)
    except PollItem.DoesNotExist:
        return Response({"error": "Poll item not found"}, status=status.HTTP_404_NOT_FOUND)

    # Check if user has already voted on this poll
    if Vote.objects.filter(poll_item__poll=poll_item.poll, user=user).exists():
        return Response({"error": "You have already voted on this poll"}, status=status.HTTP_400_BAD_REQUEST)

    # Create the vote
    Vote.objects.create(poll_item=poll_item, user=user)

    # Increment the vote count
    poll_item.votes += 1
    poll_item.save()

    # Update Firestore with new poll results
    update_firestore_poll_results(poll_item.poll)

    return Response({"message": "Vote submitted successfully"}, status=status.HTTP_201_CREATED)

def update_firestore_poll_results(poll):
    db = firestore.client()
    poll_ref = db.collection('active_polls').document(str(poll.id))
    
    poll_items = poll.items.all()
    total_votes = sum(item.votes for item in poll_items)
    
    poll_ref.update({
        'total_votes': total_votes,
        'items': [{
            'id': item.id,
            'votes': item.votes,
            'percentage': (item.votes / total_votes * 100) if total_votes > 0 else 0
        } for item in poll_items]
    })

# TODO Nearby Visions
# @api_view(['GET'])
# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
# def get_nearby_visions(request):
#     # Get user's latitude and longitude from request
#     user_lat = float(request.GET.get('latitude'))
#     user_lon = float(request.GET.get('longitude'))
    
#     # Create a point based on user's location
#     user_location = Point(user_lon, user_lat, srid=4326)
    
#     # Query for nearby visions
#     nearby_visions = Vision.with_locks.with_is_locked(request.user).filter(
#         location__distance_lte=(user_location, D(km=25))  # Within x km radius
#     ).annotate(
#         distance=Distance('location', user_location)
#     ).order_by('distance')

#     paginator = PageNumberPagination()
#     paginator.page_size = 10
#     page = paginator.paginate_queryset(nearby_visions, request)
    
#     if page is not None:
#         serializer = VisionSerializer(page, many=True)
#         return paginator.get_paginated_response(serializer.data)
#     return Response(None)

