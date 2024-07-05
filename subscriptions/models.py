from django.db import models
from users.models import Spectator, Creator

class Subscription(models.Model):
    spectator = models.ForeignKey(Spectator, on_delete=models.CASCADE)
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True)
    stripe_subscription_id = models.CharField(max_length=100, null=True)
    stripe_subscription_item_id = models.CharField(max_length=100, null=True)

    def __str__(self):
        return f'{self.spectator.user.username} subscribed to {self.creator.user.username}'
