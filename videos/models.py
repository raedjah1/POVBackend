from django.db import models
from users.models import Creator, User, Interest
from videos.visions_manager import VisionManager

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
    is_highlight = models.BooleanField(default=False)
    is_saved = models.BooleanField(default=False)
    private_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, default=None)
    # location = gis_models.PointField(null=True, blank=True)
    objects = models.Manager()  # The default manager
    with_locks = VisionManager()  # Our custom manager

    def __str__(self):
        return self.title

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vision = models.ForeignKey(Vision, on_delete=models.CASCADE, related_name='comment')
    text = models.TextField()
    likes = models.IntegerField(default=0)
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comment by {self.user.username} on {self.vision.title}'
