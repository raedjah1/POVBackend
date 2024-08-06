# videos/serializers.py
from rest_framework import serializers
from .models import Vision, Comment
from users.models import Interest, User
from users.serializers import UserSerializer, CreatorSerializer
from rest_framework import serializers
from .models import Poll, PollItem, Vote

class VisionSerializer(serializers.ModelSerializer):
    interests = serializers.PrimaryKeyRelatedField(queryset=Interest.objects.all(), many=True)
    thumbnail = serializers.CharField(max_length=500, required=False)
    url = serializers.CharField(max_length=500, required=False)
    creator = serializers.SerializerMethodField()
    aspect_ratio = serializers.CharField(max_length=4, required=False)
    is_locked = serializers.BooleanField(read_only=True)
    
    class Meta: 
        model = Vision
        fields = ['pk', 'title', 'thumbnail', 'description', 'views', 'url', 'creator', 'likes', 'interests', 'live', 'aspect_ratio', 'created_at', 'stereo_mapping', 'is_locked']
        read_only_fields = ['creator', 'likes', 'created_at', 'is_locked']

    def get_creator(self, obj):
        return CreatorSerializer(obj.creator).data
    
    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
        
    #     # If the vision is locked, remove sensitive fields
    #     if representation.get('is_locked', False):
    #         sensitive_fields = ['url']
    #         for field in sensitive_fields:
    #             representation[field] = None

    #     return representation

class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=False)
    vision = serializers.PrimaryKeyRelatedField(queryset=Vision.objects.all())
    initial_comment = serializers.PrimaryKeyRelatedField(queryset=Comment.objects.all(), required=False, allow_null=True)
    reply_user = serializers.SlugRelatedField(slug_field='username', queryset=User.objects.all(), required=False, allow_null=True)
    isLikedByUser = serializers.SerializerMethodField()
    likesCount = serializers.SerializerMethodField()

    class Meta: 
        model = Comment
        fields = ['pk', 'user', 'likesCount', 'vision', 'initial_comment', 'text', 'reply_user', 'created_at']
        read_only_fields = ['user', 'created_at']

    def get_isLikedByUser(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user in obj.likes.all()
        return False
    
    def get_likesCount(self, obj):
        return obj.likes.count()

class PollItemSerializer(serializers.ModelSerializer):
    percentage = serializers.FloatField(read_only=True)
    selected = serializers.SerializerMethodField()

    class Meta:
        model = PollItem
        fields = ['id', 'text', 'votes', 'percentage', 'selected']

    def get_selected(self, obj):
        user = self.context['request'].user
        return Vote.objects.filter(poll_item=obj, user=user).exists()

class PollSerializer(serializers.ModelSerializer):
    items = PollItemSerializer(many=True, read_only=True)
    total_votes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Poll
        fields = ['id', 'question', 'items', 'total_votes', 'created_at', 'ends_at', 'is_active']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        items = representation['items']
        total_votes = sum(item['votes'] for item in items)
        
        for item in items:
            item['percentage'] = (item['votes'] / total_votes * 100) if total_votes > 0 else 0

        representation['total_votes'] = total_votes
        return representation