from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from .models import Template
from .serializers import TemplateSerializer, TemplateSubstitutionSerializer, TemplateResponseSerializer
from rest_framework.decorators import api_view

class TemplateListCreateView(generics.ListCreateAPIView):
    queryset = Template.objects.filter(is_active=True)
    serializer_class = TemplateSerializer
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "templates_retrieved",
            "meta": {
                "total": queryset.count(),
                "limit": len(serializer.data),
                "page": 1,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False
            }
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            template = serializer.save()
            return Response({
                "success": True,
                "data": serializer.data,
                "message": "template_created",
                "meta": {}
            }, status=status.HTTP_201_CREATED)
        return Response({
            "success": False,
            "error": "validation_error",
            "message": "Invalid template data",
            "data": serializer.errors,
            "meta": {}
        }, status=status.HTTP_400_BAD_REQUEST)

class TemplateDetailView(APIView):
    def get(self, request, template_code, language="en"):
        try:
            template = Template.objects.filter(
                template_code=template_code, 
                language=language,
                is_active=True
            ).order_by('-version').first()
            
            if not template:
                return Response({
                    "success": False,
                    "error": "template_not_found",
                    "message": f"No template found for code '{template_code}' and language '{language}'",
                    "data": {},
                    "meta": {}
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = TemplateSerializer(template)
            return Response({
                "success": True,
                "data": serializer.data,
                "message": "template_retrieved",
                "meta": {}
            })

        except Exception as e:
            return Response({
                "success": False,
                "error": "server_error",
                "message": "Failed to fetch template",
                "data": {},
                "meta": {}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TemplateSubstitutionView(APIView):
    """Handle template variable substitution for Email/Push services"""
    
    def post(self, request):
        serializer = TemplateSubstitutionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "error": "validation_error",
                "message": "Invalid substitution data",
                "data": serializer.errors,
                "meta": {}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        template_code = serializer.validated_data['template_code']
        language = serializer.validated_data['language']
        variables = serializer.validated_data['variables']
        
        try:
            template = Template.objects.filter(
                template_code=template_code,
                language=language,
                is_active=True
            ).order_by('-version').first()
            
            if not template:
                return Response({
                    "success": False,
                    "error": "template_not_found",
                    "message": f"Template '{template_code}' not found",
                    "data": {},
                    "meta": {}
                }, status=status.HTTP_404_NOT_FOUND)
            
            result = template.substitute_variables(variables)
            
            return Response({
                "success": True,
                "data": result,
                "message": "template_processed",
                "meta": {}
            })
            
        except Exception as e:
            return Response({
                "success": False,
                "error": "processing_error",
                "message": "Failed to process template",
                "data": {},
                "meta": {}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def health_check(request):
    return Response({
        "success": True,
        "message": "template_service_healthy",
        "data": {"service": "template_service"},
        "meta": {}
    })

