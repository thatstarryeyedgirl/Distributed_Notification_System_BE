from rest_framework import serializers
from .models import NotificationRequest, NOTIFICATION_TYPE
import uuid
from enum import Enum

class NotificationType(str, Enum):
    email = "email"
    push = "push"

class UserDataSerializer(serializers.Serializer):
    name = serializers.CharField()
    link = serializers.URLField()
    meta = serializers.DictField(required=False, default={})

class NotificationRequestSerializer(serializers.ModelSerializer):
    notification_type = serializers.ChoiceField(choices=[(t.value, t.value) for t in NotificationType])
    user_id = serializers.UUIDField()
    template_code = serializers.CharField()
    variables = UserDataSerializer()
    request_id = serializers.CharField(required=False)
    priority = serializers.IntegerField(default=1)
    metadata = serializers.DictField(required=False, default={})

    class Meta:
        model = NotificationRequest
        fields = ['notification_type', 'user_id', 'template_code', 'variables', 
                  'request_id', 'priority', 'metadata', 'status', 'created_at']
        read_only_fields = ['status', 'created_at']

    def create(self, validated_data):
        if not validated_data.get('request_id'):
            validated_data['request_id'] = f"req_{uuid.uuid4().hex[:6]}"
        return super().create(validated_data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['variables'] = rep.get('variables') or {"name": "", "link": "", "meta": {}}
        rep['metadata'] = rep.get('metadata') or {}
        return rep


