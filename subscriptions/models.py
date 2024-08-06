from django.db import models
from users.models import Spectator, Creator, User


class Subscription(models.Model):
    spectator = models.ForeignKey(Spectator, on_delete=models.CASCADE)
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True)
    stripe_subscription_id = models.CharField(max_length=100, null=True)
    stripe_subscription_item_id = models.CharField(max_length=100, null=True)

    def __str__(self):
        return f'{self.spectator.user.username} subscribed to {self.creator.user.username}'

class Promotion(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name='promotions')
    stripe_coupon_id = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Promotion by {self.creator.user.username}: {self.description}"
