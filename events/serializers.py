# events/serializers.py
from rest_framework import serializers
from .models import Event
from videos.serializers import VisionSerializer
from users.serializers import CreatorSerializer

class EventSerializer(serializers.ModelSerializer):
    vision = VisionSerializer(required=False)
    creator = CreatorSerializer(required=False)
    
    class Meta: 
        model = Event
        fields = ['pk', 'creator', 'title', 'description', 'start_time', 'vision', 'remind_me_list']
        read_only_fields = ['creator', 'vision']
