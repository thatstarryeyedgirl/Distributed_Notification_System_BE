from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Users, Device, NotificationPreference, NotificationLog
from django.contrib.auth.password_validation import validate_password
from .utils import send_welcome_email
from enum import Enum
from datetime import datetime

class NotificationStatus(str, Enum):
    delivered = "delivered"
    pending = "pending"
    failed = "failed"

User = get_user_model()

class UsersSerializer(serializers.ModelSerializer):
    preferences = serializers.SerializerMethodField()
    devices = serializers.SerializerMethodField()

    class Meta:
        model = Users
        fields = ['user_id', 'name', 'email', 'preferences', 'devices', 'created_at']

    def get_preferences(self, obj):
        return {
            'email': obj.preferences.email,
            'push': obj.preferences.push
        }

    def get_devices(self, obj):
        devices = obj.devices.all()
        return [{'device_type': d.device_type, 'push_token': d.push_token, 'created_at': d.created_at} for d in devices]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Only add push_token if user has push preference enabled and has devices
        if instance.preferences.push and instance.devices.exists():
            data['push_token'] = instance.devices.first().push_token
        return data


class UsersPreferenceSerializer(serializers.ModelSerializer):
    email = serializers.BooleanField(required=False, default=False)
    push = serializers.BooleanField(required=False, default=False)
    
    class Meta:
        model = NotificationPreference
        fields = [ 'email', 'push']
    
    def validate(self, data):
        # Convert to boolean properly
        email = bool(data.get('email', False))
        push = bool(data.get('push', False))
        
        if email == push:
            raise serializers.ValidationError("Must choose either email OR push, not both or neither.")
        
        return data


class UsersRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password], error_messages={'required': 'Password is required from User.'})
    name = serializers.CharField(required=True, error_messages={'required': 'Name is required from User.'})
    email = serializers.EmailField(required=True, error_messages={'required': 'Email is required from User.'})
    preferences = UsersPreferenceSerializer(required=True)
    device_type = serializers.ChoiceField(choices=Device.DEVICE_TYPES, required=False, allow_null=True)
    
    class Meta:
        model = Users
        fields = ['user_id', 'name', 'email', 'password', 'preferences', 'device_type']

    def validate(self, data):
        preferences = data.get('preferences', {})
        device_type = data.get('device_type')
        
        # If user chooses push, device_type is mandatory
        if preferences.get('push') and not device_type:
            raise serializers.ValidationError({
                'device_type': 'Device type is required when push notifications are enabled.'
            })
        
        # If user chooses email, device_type should not be provided
        if preferences.get('email') and device_type:
            raise serializers.ValidationError({
                'device_type': 'Device type should not be provided for email notifications.'
            })
        
        return data
    
    def create(self, validated_data):
        preferences_data = validated_data.pop('preferences')
        device_type = validated_data.pop('device_type', None)
        user = Users.objects.create_user(**validated_data)
        
        email_pref = preferences_data.get('email', False)
        push_pref = preferences_data.get('push', False)
        
        NotificationPreference.objects.create(
            user=user,
            email=email_pref,
            push=push_pref
        )
        
        # Based on preference, either send email or create push token
        if push_pref:
            # Create device with push token for push users using specified device type
            Device.objects.create(user=user, device_type=device_type)
        elif email_pref:
            # Send welcome email with verification link for email users
            try:
                
                send_welcome_email(user)
            except Exception as e:
                print(f"Failed to send welcome email: {e}")
        
        return user
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['preferences'] = {
            'email': instance.preferences.email,
            'push': instance.preferences.push
        }
        
        # Only include push_token if user prefers push notifications
        if instance.preferences.push:
            device = instance.devices.first()
            data['push_token'] = device.push_token if device else None
        else:
            data['push_token'] = None
            
        return data


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['device_type', 'push_token', 'created_at']
        read_only_fields = ['push_token', 'created_at']
        
        def create(self, validated_data):
            return Device.objects.create(user=self.context['request'].user, **validated_data)



class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['email', 'push']


class NotificationStatusSerializer(serializers.Serializer):
    notification_id = serializers.CharField()
    status = serializers.ChoiceField(choices=[(s.value, s.value) for s in NotificationStatus])
    timestamp = serializers.DateTimeField(required=False, default=datetime.now)
    error = serializers.CharField(required=False)




