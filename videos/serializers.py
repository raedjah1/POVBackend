# videos/serializers.py
from rest_framework import serializers
from .models import Vision, Comment
from users.models import Interest, Creator, User
from users.serializers import UserSerializer, CreatorSerializer

class VisionSerializer(serializers.ModelSerializer):
    interests = serializers.PrimaryKeyRelatedField(queryset=Interest.objects.all(), many=True)
    thumbnail = serializers.CharField(max_length=500, required=False)
    url = serializers.CharField(max_length=500, required=False)
    creator = serializers.SerializerMethodField()
    aspect_ratio = serializers.CharField(max_length=4, required=False)
    
    class Meta: 
        model = Vision
        fields = ['pk', 'title', 'thumbnail', 'description', 'views', 'url', 'creator', 'likes', 'interests', 'live', 'aspect_ratio', 'created_at']
        read_only_fields = ['creator', 'likes', 'created_at',]

    def get_creator(self, obj):
        return CreatorSerializer(obj.creator).data

class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=False)
    vision = serializers.PrimaryKeyRelatedField(queryset=Vision.objects.all())
    initial_comment = serializers.PrimaryKeyRelatedField(queryset=Comment.objects.all(), required=False, allow_null=True)
    #reply_user = serializers.SlugRelatedField(slug_field='username', queryset=User.objects.all(), required=False, allow_null=True)
    
    class Meta: 
        model = Comment
        fields = ['pk', 'user', 'likes', 'vision', 'initial_comment', 'text', 'created_at']
        read_only_fields = ['user', 'created_at']
