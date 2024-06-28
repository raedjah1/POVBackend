from datetime import datetime
from django.shortcuts import render
# events/views.py
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from http import HTTPStatus
from django.db.models import Count
from .models import Event
from .serializers import EventSerializer
from videos.models import Vision
from videos.serializers import VisionSerializer
from users.models import Creator, Interest, Spectator

@api_view(['GET', 'POST'])
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
        vision = Vision.objects.get(pk=pk)
        # Implement the MUX API integration for creating a live stream
        # Set the vision's URL to the live stream URL
        vision.save()
        return Response({'message': 'Live stream created', 'vision': VisionSerializer(vision).data})
    except Exception as e:
        return Response({'message': 'There was an error', 'error': True}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_event_by_creator(request, pk):
    try:
        creator = Creator.objects.get(pk=pk)
        events = Event.objects.filter(creator=creator).order_by('start_time')
        return Response({'message': 'Successfully retrieved events', 'data': EventSerializer(events, many=True).data})
    except Exception as e:
        return Response({'message': 'There was an error', 'error': True}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_upcoming_events_by_interests(request):
    try:
        interests = request.GET.getlist('interests')
        q_interests = [Interest.objects.get(name=interest_name) for interest_name in interests]
        events = Event.objects.annotate(num_waiting=Count('remind_me_list')).filter(vision__interests__in=q_interests).filter(start_time__gte=datetime.now()).distinct().order_by('-num_waiting', 'start_time')
        return Response({'message': 'Successfully retrieved events', 'data': EventSerializer(events, many=True).data})
    except Exception as e:
        return Response({'message': 'There was an error', 'error': True}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def add_or_remove_from_remind_me_list(request, event_pk, spectator_pk):
    try:
        spectator = Spectator.objects.get(pk=spectator_pk)
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
def get_events_from_subscriptions(request, spectator_pk):
    try:
        spectator = Spectator.objects.get(pk=spectator_pk)
        events = Event.objects.annotate(num_waiting=Count('remind_me_list')).filter(creator__in=spectator.subscriptions.all()).filter(start_time__gte=datetime.now()).distinct().order_by('-num_waiting')
        return Response({'message': 'Successfully retrieved events', 'data': EventSerializer(events, many=True).data}, status=HTTPStatus.OK)
    except Exception as e:
        return Response({'message': 'There was an error', 'error': True}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
