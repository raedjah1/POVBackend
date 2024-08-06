# users/serializers.py
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password
from .models import SignInCodeRequest, User, Interest, Spectator, Creator, Badge, UserBadge

class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interest
        fields = ['pk', 'name']
        read_only_fields = ['pk']

class UserSerializer(serializers.ModelSerializer):
    class Meta: 
        model = User 
        fields = ['pk', 'username', 'profile_picture_url']
        read_only_fields = ['pk', 'profile_picture_url']

class RegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, validators=[UniqueValidator(queryset=User.objects.all())])
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    
    class Meta: 
        model = User
        fields = ['username', 'first_name', 'email', 'last_name', 'password']

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'], 
            email=validated_data['email']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class CreatorSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=False)
    
    class Meta: 
        model = Creator
        fields = ['pk', 'user', 'subscription_price', 'subscriber_count', 'is_verified']
        read_only_fields = ['pk', 'user', 'subscriber_count']

class SpectatorSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field='username', queryset=User.objects.all())
    interests = serializers.SlugRelatedField(slug_field='name', queryset=Interest.objects.all(), many=True)
    subscriptions = CreatorSerializer(required=False, many=True)
    
    class Meta: 
        model = Spectator
        fields = ['pk', 'user', 'subscriptions', 'interests', 'liked_visions', 'watch_later', 'liked_comments', 'watch_history']
        read_only_fields = ['liked_visions', 'watch_later', 'liked_comments', 'watch_history']

class SignInCodeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignInCodeRequest
        fields = ['id', 'user', 'status', 'code', 'created_at']
        read_only_fields = ['id', 'created_at']

class BadgeSerializer(serializers.ModelSerializer):
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = Badge
        fields = ['id', 'name', 'description', 'image_url', 'badge_type', 'is_locked']

    def get_is_locked(self, obj):
        user = self.context['request'].user
        return not UserBadge.objects.filter(user=user, badge=obj).exists()

class UserBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer()

    class Meta:
        model = UserBadge
        fields = ['id', 'badge', 'earned_date']