from django.db import models
from users.models import Creator, User, Interest

class Vision(models.Model):
    title = models.CharField(max_length=500)
    thumbnail = models.URLField(max_length=500, null=True)
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, null=True)
    views = models.IntegerField(default=0)
    url = models.URLField(max_length=500, null=True)
    likes = models.IntegerField(default=0)
    interests = models.ManyToManyField(Interest, blank=True)
    description = models.TextField()
    live = models.BooleanField(default=False)
    aspect_ratio = models.CharField(max_length=4, blank=True, null=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vision = models.ForeignKey(Vision, on_delete=models.CASCADE)
    text = models.TextField()
    likes = models.IntegerField(default=0)
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comment by {self.user.username} on {self.vision.title}'
