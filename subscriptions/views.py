# subscriptions/views.py
from datetime import timedelta
import os
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from http import HTTPStatus
from django.utils import timezone
import stripe.error
from pov_backend import settings
from users.serializers import CreatorSerializer
from .models import Subscription
from users.models import Spectator, Creator
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
import stripe

stripe.api_key =  os.environ.get('STRIPE_SECRET_KEY')

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def subscribe(request, pk):
    try:
        spectator = Spectator.objects.get(user=request.user)
        creator = Creator.objects.get(pk=pk)

        # Check if creator exists
        if not creator:
            return Response({'error': True, 'message': 'creator_not_found'}, status=HTTPStatus.NOT_FOUND)
        
        # Check if creator has subscription_price_id
        if not creator.subscription_price_id:
            return Response({'error': True, 'message': 'creator_has_no_subscription_price'}, status=HTTPStatus.BAD_REQUEST)

        # Check if the user has a saved card
        if not spectator.stripe_customer_id:
            return Response({'error': True, 'message': 'missing_payment_methods'}, status=HTTPStatus.BAD_REQUEST)

        # Check if the user is already subscribed
        existing_subscription = Subscription.objects.filter(spectator=spectator, creator=creator, end_date__isnull=True).first()
        if existing_subscription:
            return Response({'error': True, 'message': 'already_subscribed'}, status=HTTPStatus.BAD_REQUEST)
        
        # Ensure the spectator has a Stripe customer ID
        if not spectator.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email,
                name=f"{request.user.first_name} {request.user.last_name}"
            )
            spectator.stripe_customer_id = customer.id
            spectator.save()
        
        # Create a Subscription in Stripe
        try:
            stripe_subscription = stripe.Subscription.create(
                customer=spectator.stripe_customer_id,
                items=[{
                    'price': creator.subscription_price_id,
                }],
                payment_behavior='default_incomplete',
                payment_settings={'save_default_payment_method': 'on_subscription'},
                expand=['latest_invoice.payment_intent', 'pending_setup_intent'],
            )
            
            # A SetupIntent is required, which means we need to set up a payment method
            if stripe_subscription.pending_setup_intent is not None:
                # Cancel the SetupIntent
                stripe.SetupIntent.cancel(stripe_subscription.pending_setup_intent.id)

                # Delete the subscription and inform the client
                stripe.Subscription.delete(stripe_subscription.id)

                return Response({
                    'error': True,
                    'message': 'missing_payment_method',
                    'details': 'A valid payment method is required to create this subscription.'
                }, status=HTTPStatus.BAD_REQUEST)

            client_secret = stripe_subscription.latest_invoice.payment_intent.client_secret
            intent_type = 'payment'

            # After creating the stripe_subscription
            latest_invoice = stripe_subscription.latest_invoice
            payment_intent = latest_invoice.payment_intent

            if payment_intent.status == 'requires_confirmation':
                payment_intent.confirm()
            elif payment_intent.status == 'requires_action':
                # This means the payment requires additional authentication
                return Response({
                    'payment_requires_action': True,
                    'payment_intent_client_secret': payment_intent.client_secret
                })

            # Create a Subscription object in the database
            subscription = Subscription.objects.create(
                spectator=spectator,
                creator=creator,
                start_date=timezone.now(),
                stripe_subscription_id=stripe_subscription.id,
                stripe_subscription_item_id=stripe_subscription['items']['data'][0]['id']
            )
            
            # Add the creator to the spectator's subscriptions
            spectator.subscriptions.add(creator)
            spectator.save()
            
            # Increment the creator's subscriber count
            creator.subscriber_count += 1
            creator.save()
            
            return Response({
                'message': 'success',
                'type': intent_type,
                'client_secret': client_secret,
                'subscription_id': stripe_subscription.id
            })
        except stripe.error.StripeError as e:
            return Response({'error': True, 'message': str(e)}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return Response({'error': True, 'message': str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_subscriptions(request):
    try:
        spectator = Spectator.objects.get(user=request.user)
        return Response({'message': 'Successfully retrieved subscriptions', 'data': CreatorSerializer(spectator.subscriptions, many=True).data})
    except Exception as e:
        return Response({'error': True, 'message': 'There was an error'}, status=HTTPStatus.BAD_REQUEST)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_card(request):
    try:
        spectator = Spectator.objects.get(user=request.user)
        
        # Create or retrieve Stripe customer
        if not spectator.stripe_customer_id:
            customer = stripe.Customer.create(
                email=spectator.user.email,
            )
            spectator.stripe_customer_id = customer.id
            spectator.save()
        else:
            customer = stripe.Customer.retrieve(spectator.stripe_customer_id)

        # Create a SetupIntent
        setup_intent = stripe.SetupIntent.create(
            customer=customer.id,
            automatic_payment_methods={
                'enabled': True,
            },
        )

        return Response({
            'client_secret': setup_intent.client_secret,
            'message': 'SetupIntent created successfully'
        }, status=HTTPStatus.OK)
    except stripe.error.StripeError as e:
        return Response({'error': True, 'message': str(e)}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return Response({'error': True, 'message': str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_creator_price(request):
    try:
        creator = Creator.objects.get(user=request.user)
        new_price = request.data.get('price')
        
        if not new_price:
            return Response({'error': 'missing_price'}, status=HTTPStatus.BAD_REQUEST)
        
        # Convert price to cents for Stripe
        stripe_price = int(float(new_price) * 100)
        
        # If the creator already has a price ID, delete the existing price
        if creator.subscription_price_id:
            try:
                stripe.Price.modify(
                    creator.subscription_price_id,
                    active=False
                )
            except stripe.error.StripeError as e:
                print(f"Error deleting old price: {str(e)}")
        
        # Create a new Price object in Stripe
        try:
            new_price_object = stripe.Price.create(
                unit_amount=stripe_price,
                currency="usd",
                recurring={"interval": "month"},
                product_data={
                    "name": f"{creator.user.username}'s Subscription"
                },
            )
            
            # Update all active subscriptions to the new price
            active_subscriptions = Subscription.objects.filter(creator=creator, end_date__gt=timezone.now())
            for subscription in active_subscriptions:
                try:
                    updated_subscription = stripe.Subscription.modify(
                        subscription.stripe_subscription_id,
                        items=[{
                            'id': subscription.stripe_subscription_item_id,
                            'price': new_price_object.id,
                        }],
                        proration_behavior='always_invoice',  # or 'create_prorations' based on your preference
                    )
                    # Update local subscription object if needed
                    subscription.save()
                except stripe.error.StripeError as e:
                    print(f"Error updating subscription {subscription.id}: {str(e)}")
            
            # Update the creator's subscription price and price ID
            creator.subscription_price = new_price
            creator.subscription_price_id = new_price_object.id
            creator.save()

            return Response({
                'message': 'Subscription price updated successfully',
                'new_price': new_price,
                'stripe_price_id': new_price_object.id
            }, status=HTTPStatus.OK)
        
        except stripe.error.StripeError as e:
            return Response({'error': f'Stripe error: {str(e)}'}, status=HTTPStatus.BAD_REQUEST)
        
    except Creator.DoesNotExist:
        return Response({'error': 'Creator not found'}, status=HTTPStatus.NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_subscribed_creators(request):
    # Get the Spectator object for the authenticated user
    spectator = get_object_or_404(Spectator, user=request.user)
    
    # Get all subscribed creators
    subscribed_creators = spectator.subscriptions.all().order_by('user__username')

    # Set up pagination
    paginator = PageNumberPagination()
    paginator.page_size = 10
    page = paginator.paginate_queryset(subscribed_creators, request)

    if page is not None:
        serializer = CreatorSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    # If there's no page (i.e., no subscriptions), return an empty list
    return Response([])

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def check_subscription_status(request, creator_id):
    # Get the Creator object
    creator = get_object_or_404(Creator, pk=creator_id)
    
    try:
        # Get the Spectator object for the authenticated user
        spectator = Spectator.objects.get(user=request.user)
        
        # Check if the spectator is subscribed to the creator
        is_subscribed = spectator.subscriptions.filter(pk=creator_id).exists()
        
        return Response({
            'is_subscribed': is_subscribed,
            'creator_id': creator_id,
            'creator_username': creator.user.username
        })
    
    except Spectator.DoesNotExist:
        # If the user doesn't have a Spectator object, they're not subscribed
        return Response({
            'is_subscribed': False,
            'creator_id': creator_id,
            'creator_username': creator.user.username
        })

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def unsubscribe(request, pk):
    try:
        spectator = Spectator.objects.get(user=request.user)
        creator = Creator.objects.get(pk=pk)

        # Check if the user is subscribed
        subscription = Subscription.objects.filter(spectator=spectator, creator=creator).first()
        if not subscription:
            return Response({'error': True, 'message': 'not_subscribed'}, status=HTTPStatus.BAD_REQUEST)

        try:
            # Cancel the subscription in Stripe
            stripe_subscription = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )

            # Update the local subscription end date
            subscription.end_date = timezone.now() + timedelta(seconds=stripe_subscription.current_period_end - int(timezone.now().timestamp()))
            subscription.save()

            # Remove the creator from the spectator's subscriptions
            spectator.subscriptions.remove(creator)

            # Decrement the creator's subscriber count
            creator.subscriber_count = max(0, creator.subscriber_count - 1)
            creator.save()

            return Response({
                'message': f'Successfully unsubscribed from {creator.user.username}',
                'end_date': subscription.end_date
            })

        except stripe.error.StripeError as e:
            return Response({'error': True, 'message': str(e)}, status=HTTPStatus.BAD_REQUEST)

    except Spectator.DoesNotExist:
        return Response({'error': True, 'message': 'spectator_not_found'}, status=HTTPStatus.NOT_FOUND)
    except Creator.DoesNotExist:
        return Response({'error': True, 'message': 'creator_not_found'}, status=HTTPStatus.NOT_FOUND)
    except Exception as e:
        return Response({'error': True, 'message': str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

# For Testing Only
# @api_view(['POST'])
# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
# def add_card_test(request):
#     try:
#         spectator = Spectator.objects.get(user=request.user)
#         token = request.data.get('card_token')

#         if not token:
#             return Response({'error': 'Token is required'}, status=HTTPStatus.BAD_REQUEST)

#         # Create or retrieve Stripe customer
#         if not spectator.stripe_customer_id:
#             customer = stripe.Customer.create(
#                 email=spectator.user.email,
#                 source=token  # This adds the card to the customer
#             )
#             spectator.stripe_customer_id = customer.id
#             spectator.save()
#         else:
#             customer = stripe.Customer.retrieve(spectator.stripe_customer_id)
#             stripe.Customer.create_source(
#                 customer.id,
#                 source=token
#             )

#         return Response({
#             'message': 'Card added successfully',
#             'customer_id': customer.id
#         }, status=HTTPStatus.OK)
#     except stripe.error.StripeError as e:
#         return Response({'error': True, 'message': str(e)}, status=HTTPStatus.BAD_REQUEST)
#     except Exception as e:
#         return Response({'error': True, 'message': str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
