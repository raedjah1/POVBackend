# users/views_auth.py
import logging
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from http import HTTPStatus
from django.db.models import Count

from videos.models import Vision
from .models import User, Interest, Spectator, Creator
from .serializers import InterestSerializer, UserSerializer, CreatorSerializer, SpectatorSerializer

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
def creator_account_detail(request):
    if request.method == 'GET':
        try:
            creator_account = Creator.objects.get(user=request.user)
            creator_account_serializer = CreatorSerializer(creator_account)
            visions = Vision.objects.filter(creator=creator_account)
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
