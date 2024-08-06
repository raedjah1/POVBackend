from django.db import models
from users.models import Creator, User, Interest
from videos.visions_manager import VisionManager
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.core.validators import MinValueValidator
from django.utils import timezone

# TODO Nearby Vision, GDAL library
# from django.contrib.gis.db import models as gis_models

class Vision(models.Model):
    title = models.CharField(max_length=500)
    thumbnail = models.URLField(max_length=500, null=True)
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, null=True, related_name='vision')
    views = models.IntegerField(default=0, db_index=True)
    url = models.URLField(max_length=500, null=True)
    likes = models.IntegerField(default=0, db_index=True)
    interests = models.ManyToManyField(Interest, blank=True)
    description = models.TextField()
    live = models.BooleanField(default=False)
    aspect_ratio = models.CharField(
        max_length=6, 
        choices=[('16:9', '16:9'), ('4:3', '4:3'), ('VR180', 'VR180'), ('VR360', 'VR360')],
        blank=True, null=True, default=''
    )
    stereo_mapping = models.CharField(
        max_length=100, 
        choices=[('normal', 'Normal'), ('sidebyside', 'Side By Side'), ('topbottom', 'Top Bottom')],
        default='normal',
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    search_vector = SearchVectorField(null=True)
    is_highlight = models.BooleanField(default=False)
    is_saved = models.BooleanField(default=False)
    private_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, default=None)
    # location = gis_models.PointField(null=True, blank=True)
    objects = models.Manager()  # The default manager
    with_locks = VisionManager()  # Our custom manager

    class Meta:
        indexes = [GinIndex(fields=['search_vector'])]

    def __str__(self):
        return self.title

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vision = models.ForeignKey(Vision, on_delete=models.CASCADE, related_name='comment')
    text = models.TextField()
    likes = models.ManyToManyField(User, related_name='liked_comments', blank=True)
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comment by {self.user.username} on {self.vision.title}'
    
    @property
    def like_count(self):
        return self.likes.count()

class Poll(models.Model):
    question = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    @property
    def total_votes(self):
        return sum(item.votes for item in self.items.all())

    def __str__(self):
        return self.question

class PollItem(models.Model):
    poll = models.ForeignKey(Poll, related_name='items', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    votes = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

    @property
    def percentage(self):
        total = self.poll.total_votes
        return (self.votes / total) * 100 if total > 0 else 0

    def __str__(self):
        return f"{self.text} ({self.votes} votes)"

class Vote(models.Model):
    poll_item = models.ForeignKey(PollItem, related_name='votes_cast', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('poll_item', 'user')

    def __str__(self):
        return f"{self.user.username} voted for {self.poll_item.text}"