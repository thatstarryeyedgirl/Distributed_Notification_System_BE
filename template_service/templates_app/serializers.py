from rest_framework import serializers
from .models import Template

class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ['template_code', 'language', 'subject', 'body', 'version', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['version', 'created_at', 'updated_at']

class TemplateSubstitutionSerializer(serializers.Serializer):
    template_code = serializers.CharField()
    language = serializers.CharField(default='en')
    variables = serializers.DictField()
    
class TemplateResponseSerializer(serializers.Serializer):
    subject = serializers.CharField()
    body = serializers.CharField()

