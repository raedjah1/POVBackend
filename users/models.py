# users/models.py
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex

class User(User):
    profile_picture_url = models.CharField(
        max_length=400,
        default='https://res.cloudinary.com/pov/image/upload/v1667553173/defaultPic_s89yno.png'
    )
    cover_picture_url = models.CharField(
        max_length=400,
        default='https://res.cloudinary.com/pov/image/upload/v1667553173/defaultPic_s89yno.png'
    )
    is_spectator = models.BooleanField(default=False)
    is_creator = models.BooleanField(default=False)
    sign_in_method = models.CharField(
        max_length=10,
        choices=[
            ('apple', 'Apple'),
            ('google', 'Google'), 
            ('facebook', 'Facebook'),
            ('email', 'Email')
        ],
        default='email'
    )

    def __str__(self):
        return self.username

class Interest(models.Model):
    name = models.CharField(max_length=35, unique=True)

    def __str__(self):
        return self.name

class Spectator(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    subscriptions = models.ManyToManyField('Creator', blank=True, db_index=True)
    liked_visions = models.ManyToManyField('videos.Vision', blank=True, related_name='liked_by')
    watch_later = models.ManyToManyField('videos.Vision', blank=True, related_name='watch_later_by')
    liked_comments = models.ManyToManyField('videos.Comment', blank=True)
    watch_history = models.ManyToManyField('videos.Vision', blank=True, related_name='watch_history_by')
    interests = models.ManyToManyField('Interest', blank=True)
    stripe_customer_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.user.username

class Creator(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    subscription_price = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    subscriber_count = models.IntegerField(default=0)
    bio = models.TextField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    subscription_price_id = models.CharField(max_length=100, null=True, blank=True) 
    search_vector = SearchVectorField(null=True)

    class Meta:
        indexes = [GinIndex(fields=['search_vector'])]

    def __str__(self):
        return self.user.username

class SignInCodeRequest(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, default=None)
    status = models.CharField(
        max_length=10,
        choices=[('pending', 'Pending'), ('success', 'Success')],
        default='pending'
    )
    code = models.CharField(max_length=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SignInCodeRequest {self.id}: {self.status}"

    class Meta:
        ordering = ['-created_at']

class BadgeType(models.TextChoices):
    COMMENT = 'CM', 'Comment'
    SUPER_FAN = 'SF', 'Super Fan'
    SUPPORTER = 'SP', 'Supporter'
    EARLY_BIRD = 'EB', 'Early Bird'
    COMMENT_KING = 'CK', 'Comment King'
    TOP_SUPPORTER = 'TS', 'Top Supporter'

class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image_url = models.URLField()
    badge_type = models.CharField(max_length=2, choices=BadgeType.choices)
    
    def __str__(self):
        return self.name

class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge')

    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"