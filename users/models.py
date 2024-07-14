# users/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    profile_picture_url = models.CharField(
        max_length=400,
        default='https://res.cloudinary.com/pov/image/upload/v1667553173/defaultPic_s89yno.png'
    )
    is_spectator = models.BooleanField(default=False)
    is_creator = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    def __str__(self):
        return self.username

class Interest(models.Model):
    name = models.CharField(max_length=35, unique=True)

    def __str__(self):
        return self.name

class Spectator(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    interests = models.ManyToManyField('Interest', blank=True)
    subscriptions = models.ManyToManyField('Creator', blank=True)
    liked_visions = models.ManyToManyField('videos.Vision', blank=True, related_name='liked_by')
    watch_later = models.ManyToManyField('videos.Vision', blank=True, related_name='watch_later_by')
    liked_comments = models.ManyToManyField('videos.Comment', blank=True)
    watch_history = models.ManyToManyField('videos.Vision', blank=True, related_name='watch_history_by')

    def __str__(self):
        return self.user.username

class Creator(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    subscription_price = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    subscriber_count = models.IntegerField(default=0)
    bio = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.user.username
