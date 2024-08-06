from datetime import datetime
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from http import HTTPStatus
from django.db.models import Count
import cloudinary.uploader
from pov_backend import settings
from .models import Event
from .serializers import EventSerializer
from videos.models import Vision
from videos.serializers import VisionSerializer
from users.models import Creator, Interest, Spectator
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.db.models import Count, Q
from django.utils import timezone
from .models import Event, Spectator
from .serializers import EventSerializer
from django.db.models import Count, Q, Case, When, BooleanField
from rest_framework.authentication import TokenAuthentication

@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_create_delete_events(request):
    if request.method == 'GET':
        try:
            events = Event.objects.all()
            serialized_events = EventSerializer(events, many=True)
            return Response({'message': 'Successfully retrieved events', 'data': serialized_events.data}, status=HTTPStatus.OK)
        except Exception as e:
            return Response({'message': 'There was an error', 'error': True}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    elif request.method == 'POST':
        try:
            event_serializer = EventSerializer(data=request.data)
            if event_serializer.is_valid():
                event = event_serializer.save()
                creator = Creator.objects.get(user=request.user)
                event.creator = creator
                vision = Vision.objects.create(title=event.title, thumbnail='thumbnail', creator=creator, description=event.description)
                thumbnail = request.FILES.get('thumbnail', None)
            
                if thumbnail:
                    thumbnail_res = cloudinary.uploader.upload(thumbnail, public_id=f'{request.user.username}-{vision.pk}-thumbnail', unique_filename=False, overwrite=True)
                    vision.thumbnail = thumbnail_res['secure_url']
                else:
                    return Response({'message': 'Bad request'}, status=HTTPStatus.BAD_REQUEST)

                for interest_pk in request.data['interests']:
                    interest = Interest.objects.get(pk=interest_pk)
                    vision.interests.add(interest)

                event.vision = vision
                event.save()
                return Response({'message': 'Successfully created event', 'data': EventSerializer(event).data, 'id': vision.pk}, status=HTTPStatus.OK)
            else:
                return Response({'message': 'There was an error', 'error': event_serializer.errors}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'message': 'There was an error', 'error': True}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['PUT', 'DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def edit_or_delete_events(request, pk):
    if request.method == 'PUT':
        pass  # Implement editing logic
    elif request.method == 'DELETE':
        try:
            event = Event.objects.get(pk=pk)
            event.delete()
            return Response({'message': 'Successfully deleted event'}, status=HTTPStatus.OK)
        except Exception as e:
            return Response({'message': 'There was an error', 'error': True}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def activate_event_livestream(request, pk):
    try:
        event = Event.objects.get(pk=pk)
        vision_obj = event.vision

        if vision_obj:
            vision_instance = vision_obj.save()
            vision_instance.creator = Creator.objects.get(user=request.user)
            vision_instance.is_live = True
            
            # Set the URL for HLS playback
            vision_instance.url = f'{settings.HOST}/{vision_instance.pk}.m3u8'
            
            # Get thumbnail upload
            vision_instance.save()
            
            # Generate RTMP stream link
            rtmp_stream_link = f'rtmp://{settings.RTMP_HOST}/stream/{vision_instance.pk}'
            
            # Update event with live vision
            event.vision = vision_instance
            event.save()
            
            return Response({
                'message': 'Successfully activated event livestream',
                'vision_id': vision_instance.pk,
                'hls_url': vision_instance.url,
                'rtmp_stream_link': rtmp_stream_link
            }, status=HTTPStatus.OK)
        else:
            return Response({'message': 'Invalid vision data', 'error': vision_obj.errors}, status=HTTPStatus.BAD_REQUEST)
    except Event.DoesNotExist:
        return Response({'message': 'Event not found', 'error': True}, status=HTTPStatus.NOT_FOUND)
    except Exception as e:
        return Response({'message': 'There was an error', 'error': str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_event_by_creator(request, pk):
    try:
        creator = Creator.objects.get(pk=pk)
        events = Event.objects.filter(creator=creator).order_by('start_time')
        return Response({'message': 'Successfully retrieved events', 'data': EventSerializer(events, many=True).data})
    except Exception as e:
        return Response({'message': 'There was an error', 'error': True}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_upcoming_events_by_interests(request):
    try:
        interests = request.GET.getlist('interests')
        q_interests = [Interest.objects.get(name=interest_name) for interest_name in interests]
        events = Event.objects.annotate(num_waiting=Count('remind_me_list')).filter(vision__interests__in=q_interests).filter(start_time__gte=datetime.now()).distinct().order_by('-num_waiting', 'start_time')
        return Response({'message': 'Successfully retrieved events', 'data': EventSerializer(events, many=True).data})
    except Exception as e:
        return Response({'message': 'There was an error', 'error': True}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_or_remove_from_remind_me_list(request, event_pk):
    try:
        spectator = Spectator.objects.get(user=request.user)
        event = Event.objects.get(pk=event_pk)
        if spectator in event.remind_me_list.all():
            event.remind_me_list.remove(spectator)
            return Response({'message': 'Spectator successfully removed from remind me list'}, status=HTTPStatus.OK)
        else:
            event.remind_me_list.add(spectator)
            event.save()
            return Response({'message': 'Spectator successfully added to remind me list'}, status=HTTPStatus.OK)
    except Exception as e:
        return Response({'message': 'There was an error', 'error': True}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_events_from_subscriptions(request):
    try:
        spectator = Spectator.objects.get(user=request.user)
        events = Event.objects.annotate(num_waiting=Count('remind_me_list')).filter(creator__in=spectator.subscriptions.all()).filter(start_time__gte=datetime.now()).distinct().order_by('-num_waiting')
        return Response({'message': 'Successfully retrieved events', 'data': EventSerializer(events, many=True).data}, status=HTTPStatus.OK)
    except Exception as e:
        return Response({'message': 'There was an error', 'error': True}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_recommended_events(request):
    # Get the current user's spectator object
    try:
        spectator = Spectator.objects.get(user=request.user)
    except Spectator.DoesNotExist:
        return Response({"error": "Spectator profile not found"}, status=400)

    # Get the user's interests
    user_interests = spectator.interests.all()

    # Get the creators the user is subscribed to
    subscribed_creators = spectator.subscriptions.all()

    # Get current datetime
    now = timezone.now()

    # Query for recommended events
    recommended_events = Event.objects.filter(
        Q(vision__interests__in=user_interests) | Q(creator__in=subscribed_creators),
        start_time__gt=now  # Only future events
    ).annotate(
        remind_me_count=Count('remind_me_list'),
        is_subscribed_creator=Case(
            When(creator__in=subscribed_creators, then=True),
            default=False,
            output_field=BooleanField()
        )
    ).order_by('-is_subscribed_creator', '-remind_me_count', 'start_time').distinct()

    # Pagination
    paginator = PageNumberPagination()
    paginator.page_size = 10  # You can adjust this number
    paginated_events = paginator.paginate_queryset(recommended_events, request)

    # Serialize the events
    serializer = EventSerializer(paginated_events, many=True, context={'user': request.user})

    return paginator.get_paginated_response(serializer.data)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_upcoming_events(request):
    # Get the current user's spectator object
    try:
        spectator = Spectator.objects.get(user=request.user)
    except Spectator.DoesNotExist:
        return Response({"error": "Spectator profile not found"}, status=400)

    # Get the user's interests
    user_interests = spectator.interests.all()

    # Get the creators the user is subscribed to
    subscribed_creators = spectator.subscriptions.all()

    # Get current datetime
    now = timezone.now()

    # Query for upcoming events
    upcoming_events = Event.objects.filter(
        Q(vision__interests__in=user_interests) | Q(creator__in=subscribed_creators),
        start_time__gt=now  # Only future events
    ).annotate(
        is_subscribed_creator=Case(
            When(creator__in=subscribed_creators, then=True),
            default=False,
            output_field=BooleanField()
        )
    ).order_by('-is_subscribed_creator', 'start_time').distinct()

    # Pagination
    paginator = PageNumberPagination()
    paginator.page_size = 10  # You can adjust this number
    paginated_events = paginator.paginate_queryset(upcoming_events, request)

    # Serialize the events
    serializer = EventSerializer(paginated_events, many=True, context={'user': request.user})

    return paginator.get_paginated_response(serializer.data)
