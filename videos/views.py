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
from users.models import Interest, Spectator, Creator, User
from datetime import datetime
import os
import mux_python

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
        thumbnail = request.FILES['_thumbnail']
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
            visions = Vision.objects.filter(~Q(url=None) & Q(is_private = False)).order_by('-created_at', '-likes')
        else:
            visions = Vision.objects.filter(interests__in=spectator_interests).filter(~Q(url=None) & Q(is_private = False)).distinct().order_by('-created_at', '-likes')
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
        visions = creator.vision_set.filter(~Q(url=None)) if request.user.pk == creator.pk else creator.vision_set.filter(~Q(url=None) & Q(is_private = False))
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
        visions = Vision.objects.filter(interests__in=interests).filter(~Q(url=None) & Q(is_private = False)).distinct().order_by('-created_at', '-likes')
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

@api_view(['GET'])
def get_recommended_visions_from_subs(request):
    spectatorSubs = Spectator.objects.get(user = request.user).subscriptions.all()
    try:
        
        paginator = PageNumberPagination()
        paginator.page_size = 10
        visions  = Vision.objects.filter(creator__in = spectatorSubs).filter(~Q(url = None) & Q(is_private = False)).distinct().order_by('-created_at', '-likes')
        results = paginator.paginate_queryset(visions, request)
        serializedVisions = VisionSerializer(results, many=True)
        return Response({
            'message': 'successfully retrieved visions', 
            'data': serializedVisions.data, 
            'size': len(visions),
            'next': paginator.get_next_link(), 
            'prev': paginator.get_previous_link()
            })
    except Exception as e:
        print(e)
        return Response({
            'error': True
        }, status=HTTPStatus.BAD_REQUEST)  

@api_view(['GET'])
def get_watch_later(request):
    try:
        spectator = Spectator.objects.get(user = request.user)
        visions = VisionSerializer(spectator.watch_later.all(), many=True)
        return Response({
            'message': 'successfully retrieved watch later', 
            'data': visions.data
        })
    except Exception as e: 
        print(e)
        return Response({
            'error': True, 
        })  
    
@api_view(['POST'])
def add_to_watch_later(request, vision_pk):
    try:
        vision = Vision.objects.get(pk = vision_pk)
        spectator = Spectator.objects.get(user = request.user)
        spectator.watch_later.add(vision)
        return Response({
            'message': 'Successfully added to watch later'
        })
    except Exception as e: 
        print(e)
        return Response({
            'error': True, 
        })

@api_view(['POST'])
def remove_from_watch_later(request, vision_pk):
    try:
        vision = Vision.objects.get(pk = vision_pk)
        spectator = Spectator.objects.get(user = request.user)
        spectator.watch_later.remove(vision)
        return Response({
            'message': 'Successfully removed from watch later'
        })
    except Exception as e: 
        print(e)
        return Response({
            'error': True, 
        })
    
@api_view(['GET'])
def get_watch_history(request):
    try:
        spectator = Spectator.objects.get(user = request.user)
        visions = VisionSerializer(spectator.watch_history.all(), many=True)
        return Response({
            'message': 'successfully retrieved watch later', 
            'data': visions.data
        })
    except Exception as e: 
        print(e)
        return Response({
            'error': True, 
        })  

@api_view(['POST'])
def add_to_watch_history(request, vision_pk):
    try:
        spectator = Spectator.objects.get(user = request.user)
        if spectator.watch_history.filter(pk = vision_pk).count() > 0:
            vision = Vision.objects.get(pk = vision_pk)
            spectator.watch_history.remove(vision)
            spectator.watch_history.add(vision)
        else:
            vision = Vision.objects.get(pk = vision_pk)
            spectator.watch_history.add(vision)
        return Response({
            'message': 'Successfully added to watch History'
        }, HTTPStatus.OK)
    except Exception as e: 
        print(e)
        return Response({
            'error': True, 
        })  

@api_view(['POST'])
def remove_from_watch_history(request, vision_pk):
    try:
        spectator = Spectator.objects.get(user = request.user)
        vision = Vision.objects.get(pk = vision_pk)
        spectator.watch_history.remove(vision)
        return Response({
            'message': 'Successfully removed from watch History'
        }, HTTPStatus.OK)
    except Exception as e: 
        print(e)
        return Response({
            'error': True, 
        })  

@api_view(['POST'])
def clear_watch_history(request):
    try:
        spectator = Spectator.objects.get(user = request.user)
        spectator.watch_history.clear()
        return Response({
            'message': 'Successfully cleared watch history!'
        }, HTTPStatus.OK)
    except Exception as e: 
        print(e)
        return Response({
            'error': True, 
        })  

@api_view(['POST'])
def post_comment(request):
    try:
        commentSerializer = CommentSerializer(data = request.data)
        if commentSerializer.is_valid():
            commentObj = commentSerializer.save()
            commentObj.user = User.objects.get(pk = request.user.pk)
            commentObj.save()
            return Response({
                'message': 'Comment Successfully posted!', 
                'data': commentSerializer.data
            }, status = HTTPStatus.CREATED)
        else:
            print(commentSerializer.errors)
    except Exception as e:
        print(e)
        return Response({
            'error': True, 
            'message': 'There was an error adding the comment'
        })

@api_view(['GET'])
def get_comments(request, vision_id):
    try:
        vision = Vision.objects.get(pk = vision_id)
        comments = CommentSerializer(vision.comment_set.all().filter(initial_comment = None).order_by('-likes', '-created_at'), many=True)
        return Response({
            'message': 'Comments Successfully retrieved!',
             'data': comments.data
        }, status = HTTPStatus.OK)
    except Exception as e:
        print(e)
        return Response({
            'error': True, 
            'message': 'There was an error'
        })

# @api_view(['GET'])
# def get_comment_replies(request, comment_id):
#     try:
#         initial_comment = Comment.objects.get(pk = comment_id)
#         comment_replies  = CommentSerializer(initial_comment.comment_set.all().order_by('-likes', '-created_at'), many=True)
#         return Response({
#             'message': 'Comment Replies retrieved successfully!',
#             'data': comment_replies.data
#         }, status = HTTPStatus.OK)
#     except Exception as e:
#         print(e)
#         return Response({
#             'error': True, 
#             'message': 'There was an error'
#         })


@api_view(['DELETE', 'POST'])
def delete_or_like_or_dislike_comment(request, comment_id):
    if request.method == 'DELETE':
        try:
            comment = Comment.objects.get(pk = comment_id)
            comment.delete()
            return Response({
                'message':'Comment Deleted Successfully!'
            })
        except Exception as e:
            print(e)
            return Response({
                'error': True, 
                'message': 'There was an error'
            })
    elif request.method == 'POST':
        try:
            comment = Comment.objects.get(pk = comment_id)
            spectator = Spectator.objects.get(user = request.user)
            if comment in spectator.liked_comments.all():
                comment.likes -= 1
                spectator.liked_comments.remove(comment)
                comment.save()
                spectator.save()
                return Response({
                    'message': 'Comment disliked'
                })
            else:
                comment.likes+=1
                spectator.liked_comments.add(comment)
                comment.save()
                spectator.save()
                return Response({
                    'message': 'Comment liked'
                })
        except Exception as e:
            print(e)
            return Response({
                'error': True, 
                'message': 'There was an error'
            })


@api_view(['POST'])
def create_livestream_vision(request):
    pass
    # try:
    #     visionData = VisionSerializer(data= request.data)
    #     if visionData.is_valid():
    #         vision = visionData.save()
    #         live_api = mux_python.LiveStreamsApi(mux_python.ApiClient(configuration=configuration))
    #         new_asset_settings = mux_python.CreateAssetRequest(playback_policy=[mux_python.PlaybackPolicy.PUBLIC])
    #         create_livestream_request = mux_python.CreateLiveStreamRequest(playback_policy=[mux_python.PlaybackPolicy.PUBLIC], new_asset_settings=new_asset_settings)
    #         create_livestream_response = live_api.create_live_stream(create_livestream_request)
    #         print(create_livestream_response.data.id)
    #         data = {
    #             'id': create_livestream_response.data.id, 
    #             'stream_key': create_livestream_response.data.stream_key,
    #             "status": create_livestream_response.data.status,
    #             "playback_ids": [{
    #                 "policy": create_livestream_response.data.playback_ids[0].policy,
    #                 "id": create_livestream_response.data.playback_ids[0].id
    #             }],
    #             "created_at": create_livestream_response.data.created_at
    #         }
    #         creator = Creator.objects.get(user = request.user)
    #         vision.creator = creator
    #         vision.url = f'https://stream.mux.com/{data["playback_ids"][0]["id"]}.m3u8'
    #         vision.save()
        
    #         return Response({
    #             'message': 'Live stream created', 
    #             'livestream_data': data,
    #             'id': vision.pk
    #         })
    # except Exception as e:
    #     print(e)
    #     return Response({
    #         'messaage': 'error!'
    #     }, status=HTTPStatus.BAD_REQUEST)

@api_view(['DELETE'])
def delete_vision(request, pk):
    try:
        vision = Vision.objects.get(pk = pk)
        vision.delete()
        return Response({
            'message': 'Vision Deleted Successfully'
        })
    except Exception as e:
        print(e)
        return Response({
            'messaage': 'error!'
        }, status=HTTPStatus.BAD_REQUEST)

@api_view(['GET'])
def search_visions(request):
    try:
        query = request.GET.get('search', '')
        visions = Vision.objects.filter(title__icontains = query)
        serializedVisions = VisionSerializer(visions, many = True)
        return Response({
            'message': 'Successfully retrieved visions',
            'data': serializedVisions.data
        }, HTTPStatus.OK)
    except Exception as e:
        print(e)
        response = {
            'message': e,
            'error': True
        }
        return Response(response, status = HTTPStatus.INTERNAL_SERVER_ERROR)
