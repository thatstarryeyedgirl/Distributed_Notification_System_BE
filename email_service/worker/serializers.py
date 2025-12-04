from rest_framework import serializers
from .models import EmailNotification, DeliveryLog


class EmailNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailNotification
        fields = ['id', 'request_id', 'to_email', 'template_code', 'variables', 'status', 'attempts', 'created_at', 'updated_at']


class DeliveryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryLog
        fields = ['id', 'notification', 'status', 'message_id', 'provider_response', 'timestamp']


