from rest_framework import serializers
from .models import Admins
from django.contrib.auth.hashers import check_password


class AdminsRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, error_messages={'required': 'Admin must input a password'})
    email = serializers.EmailField(required=True, error_messages={'required': 'Admin must have an email'})
    name = serializers.CharField(required=True, error_messages={'required': 'Name is required'})

    class Meta:
        model = Admins
        fields = ['email', 'name', 'password']
        
    def validate(self, attrs):
        errors = {}
        email = attrs.get('email')
        
        if Admins.objects.filter(email=email).exists():
            errors['email'] = "An admin with this email already exists."
            
        password = attrs.get('password')
        if len(password) < 12:
            errors['password'] = "Password must be at least 12 characters long."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        admin = Admins.objects.create_admin(
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password']
        )
        return admin


class AdminsSerializer(serializers.ModelSerializer):
    admin_id = serializers.CharField(source='id', read_only=True)
    
    class Meta:
        model = Admins
        fields = ['admin_id', 'email', 'name', 'created_at']






