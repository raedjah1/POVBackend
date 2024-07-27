# payments/views.py
from rest_framework.response import Response
from rest_framework.decorators import api_view
from http import HTTPStatus
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from users.models import Creator, Spectator
from videos.models import Comment
from .models import Tip, Transaction
from .serializers import TransactionSerializer
import stripe
from rest_framework import status

@api_view(['GET'])
def get_transactions(request):
    try:
        transactions = Transaction.objects.filter(user=request.user)
        return Response({'message': 'Successfully retrieved transactions', 'data': TransactionSerializer(transactions, many=True).data})
    except Exception as e:
        return Response({'error': True, 'message': 'There was an error'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def create_transaction(request):
    try:
        transaction_serializer = TransactionSerializer(data=request.data)
        if transaction_serializer.is_valid():
            transaction_serializer.save(user=request.user)
            return Response({'message': 'Transaction created successfully', 'data': transaction_serializer.data}, status=HTTPStatus.CREATED)
        else:
            return Response({'message': 'There was an error', 'errors': transaction_serializer.errors}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return Response({'error': True, 'message': 'There was an error'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def send_tip(request):
    try:
        amount = float(request.data.get('amount'))
        creator_id = request.data.get('creator_id')
        comment_text = request.data.get('comment_text')

        spectator = Spectator.objects.get(user=request.user)
        creator = Creator.objects.get(pk=creator_id)

        # Check if creator exists
        if not creator:
            return Response({'error': True, 'message': 'creator_not_found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if the user has a saved payment method
        if not spectator.stripe_customer_id:
            return Response({'error': True, 'message': 'missing_payment_method'}, status=status.HTTP_400_BAD_REQUEST)

        # Create a PaymentIntent
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency='usd',
                customer=spectator.stripe_customer_id,
                metadata={
                    'tip_for': creator.user.username,
                    'from_user': request.user.username
                }
            )

            # Create a new comment
            created_comment = None
            if comment_text:
                created_comment = Comment.objects.create(
                    user=request.user,
                    creator=creator,
                    text=comment_text
                )

            # Create a Tip record
            tip = Tip.objects.create(
                amount=amount,
                message=comment_text,
                user=request.user,
                creator=creator,
                comment=created_comment
            )

            return Response({
                'status': 'success',
                'tip': tip
            })

        except stripe.error.StripeError as e:
            return Response({'error': True, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({'error': True, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
