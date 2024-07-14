import logging
import cloudinary.uploader
import boto3
from botocore.client import Config
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from http import HTTPStatus
from django.db.models import Count, Q
from .models import Vision, Comment
from .serializers import VisionSerializer, CommentSerializer
from users.models import Interest, Spectator, Creator
from datetime import datetime
import os

config = cloudinary.config(
    cloud_name = 'pov', 
    api_key = os.getenv('CLOUDINARY_API_KEY'), 
    api_secret = os.getenv('CLOUDINARY_API_SECRET'),
    secure=True)

logger = logging.getLogger(__name__)

# Correct usage in views
@api_view(['POST'])
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

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def upload_thumbnail(request, vision_pk):
    try:
        vision = Vision.objects.get(pk=vision_pk)
        thumbnail = request.FILES['thumbnail']
        thumbnail_res = cloudinary.uploader.upload(thumbnail, public_id=f'{request.user.username}-{vision.title}-thumbnail', unique_filename=False, overwrite=True)
        vision.thumbnail = thumbnail_res['secure_url']
        vision.save()
        return Response({'message': 'Successfully uploaded thumbnail'})
    except Exception as e:
        logger.error(f"Error uploading thumbnail: {e}")
        return Response({'error': True, 'message': 'There was an error'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['PUT', 'GET'])
@permission_classes([IsAuthenticated])
def update_or_get_vision_info(request, vision_pk):
    if request.method == 'GET':
        try:
            vision = Vision.objects.get(pk=vision_pk)
            return Response({'message': 'Successfully retrieved vision', 'data': VisionSerializer(vision).data})
        except Vision.DoesNotExist:
            return Response({'error': True, 'message': 'Vision not found'}, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving vision info: {e}")
            return Response({'error': True, 'message': 'There was an error'}, status=HTTPStatus.BAD_REQUEST)
    elif request.method == 'PUT':
        try:
            vision = Vision.objects.get(pk=vision_pk)
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
@permission_classes([IsAuthenticated])
def get_recommended_visions(request):
    try:
        spectator_interests = Spectator.objects.get(user=request.user).interests.all()
        paginator = PageNumberPagination()
        paginator.page_size = 10
        if not spectator_interests.exists():
            visions = Vision.objects.filter(~Q(url=None)).order_by('-created_at', '-likes')
        else:
            visions = Vision.objects.filter(interests__in=spectator_interests).filter(~Q(url=None)).distinct().order_by('-created_at', '-likes')
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
        visions = creator.vision_set.filter(~Q(url=None))
        paginator = PageNumberPagination()
        paginator.page_size = 10
        results = paginator.paginate_queryset(visions, request)
        return paginator.get_paginated_response(VisionSerializer(results, many=True).data)
    except Exception as e:
        logger.error(f"Error fetching visions by creator: {e}")
        return Response({'error': True}, status=HTTPStatus.BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_visions_by_interest(request):
    try:
        interests = [Interest.objects.get(name=interest_name) for interest_name in request.data['interests']]
        visions = Vision.objects.filter(interests__in=interests).filter(~Q(url=None)).distinct().order_by('-created_at', '-likes')
        paginator = PageNumberPagination()
        paginator.page_size = 10
        results = paginator.paginate_queryset(visions, request)
        return paginator.get_paginated_response(VisionSerializer(results, many=True).data)
    except Exception as e:
        logger.error(f"Error fetching visions by interest: {e}")
        return Response({'error': True}, status=HTTPStatus.BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def like_or_dislike_vision(request, pk):
    try:
        vision = Vision.objects.get(pk=pk)
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
