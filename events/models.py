from django.db import models
from users.models import Creator, Spectator
from videos.models import Vision

class Event(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField()
    vision = models.OneToOneField(Vision, on_delete=models.CASCADE, null=True, blank=True)
    start_time = models.DateTimeField()
    remind_me_list = models.ManyToManyField(Spectator, blank=True)

    def __str__(self):
        return self.title
