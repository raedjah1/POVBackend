# subscriptions/views.py
from rest_framework.response import Response
from rest_framework.decorators import api_view
from http import HTTPStatus

from users.serializers import CreatorSerializer, SpectatorSerializer
from .models import Subscription
from .serializers import SubscriptionSerializer
from users.models import Spectator, Creator

@api_view(['POST'])
def subscribe(request, pk):
    try:
        spectator = Spectator.objects.get(user=request.user)
        creator = Creator.objects.get(pk=pk)
        spectator.subscriptions.add(creator)
        spectator.save()
        return Response({'message': f'Successfully subscribed to {creator.user.username}', 'data': SpectatorSerializer(spectator).data})
    except Exception as e:
        return Response({'error': True, 'message': 'There was an error'}, status=HTTPStatus.BAD_REQUEST)

@api_view(['GET'])
def get_subscriptions(request):
    try:
        spectator = Spectator.objects.get(user=request.user)
        return Response({'message': 'Successfully retrieved subscriptions', 'data': CreatorSerializer(spectator.subscriptions, many=True).data})
    except Exception as e:
        return Response({'error': True, 'message': 'There was an error'}, status=HTTPStatus.BAD_REQUEST)
