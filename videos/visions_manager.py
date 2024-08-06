from django.db import models
from django.db.models import Exists, OuterRef, Case, When, BooleanField

class VisionManager(models.Manager):
    def with_is_locked(self, user):
        from users.models import Spectator  # Import here to avoid circular import

        spectator = Spectator.objects.get(user=user)
        subscribed_creators = spectator.subscriptions.all()

        return self.annotate(
            is_locked=Case(
                When(is_highlight=True, then=False),
                default=~Exists(subscribed_creators.filter(user=OuterRef('creator__user'))),
                output_field=BooleanField()
            )
        )
    