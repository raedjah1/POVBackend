# payments/views.py
from rest_framework.response import Response
from rest_framework.decorators import api_view
from http import HTTPStatus
from .models import Transaction
from .serializers import TransactionSerializer

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
