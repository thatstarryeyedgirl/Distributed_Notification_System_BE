from rest_framework import serializers
from .models import PushNotification, PushDeliveryLog

class VariablesSerializer(serializers.Serializer):
    title = serializers.CharField(required=True)
    body = serializers.CharField(required=True)
    image = serializers.URLField(required=True)
    link = serializers.URLField(required=True)
    data = serializers.DictField(required=False, default=dict)

class PushNotificationSerializer(serializers.ModelSerializer):
    variables = VariablesSerializer()

    class Meta:
        model = PushNotification
        fields = [
            'id', 'request_id', 'user_id', 'to_device_token',
            'template_code', 'variables', 'priority', 'metadata',
            'status', 'attempts', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'attempts', 'created_at', 'updated_at']

class PushDeliveryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushDeliveryLog
        fields = ['id', 'notification', 'status', 'provider_response', 'provider_message_id', 'created_at']

