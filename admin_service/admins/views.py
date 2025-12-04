from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken, TokenError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import smart_bytes, force_str
from datetime import timedelta
from .models import Admins, AdminAPIKey
from .serializers import AdminsRegisterSerializer, AdminsSerializer
import requests
from django.conf import settings

class AdminRegisterView(generics.CreateAPIView):
    serializer_class = AdminsRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            admin = serializer.save()
            
            # Automatically create API keys for all services
            services = [
                'api_gateway_service',
                'user_service', 
                'template_service',
                'email_service',
                'push_service'
            ]
            
            api_keys = {}
            for service in services:
                api_key = AdminAPIKey.objects.create(
                    admin=admin,
                    service_name=service
                )
                api_keys[service] = api_key.key
            
            return Response({
                "success": True,
                "message": "admin_created",
                "data": {
                    "admin": AdminsSerializer(admin).data,
                    "api_keys": api_keys
                }
            }, status=status.HTTP_201_CREATED)
        return Response({
            "success": False,
            "error": "validation_error",
            "data": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class AdminLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        
        if not email or not password:
            return Response({"error": "email and password required"}, status=400)
        
        admin = Admins.objects.filter(email=email).first()
        if not admin or not admin.check_password(password):
            return Response({"error": "Invalid credentials"}, status=401)
        
        refresh = RefreshToken.for_user(admin)
        return Response({
            "admin": AdminsSerializer(admin).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        })

class APIKeyCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        service_name = request.data.get('service_name')
        if not service_name:
            return Response({"error": "service_name required"}, status=400)
        
        # Check if API key already exists for this service
        existing_key = AdminAPIKey.objects.filter(
            admin=request.user, 
            service_name=service_name,
            active=True
        ).first()
        
        if existing_key:
            return Response({
                "success": True,
                "message": "API key already exists",
                "data": {
                    "service_name": service_name,
                    "api_key": existing_key.key,
                    "created_at": existing_key.created_at
                }
            })
        
        # Create new API key
        api_key = AdminAPIKey.objects.create(
            admin=request.user,
            service_name=service_name
        )
        
        return Response({
            "success": True,
            "message": "API key created",
            "data": {
                "service_name": service_name,
                "api_key": api_key.key,
                "created_at": api_key.created_at
            }
        }, status=201)

class APIKeyListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        api_keys = AdminAPIKey.objects.filter(admin=request.user, active=True)
        data = [{
            "service_name": key.service_name,
            "api_key": key.key,
            "created_at": key.created_at
        } for key in api_keys]
        
        return Response({
            "success": True,
            "data": data
        })

class APIKeyRevokeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, service_name):
        api_key = AdminAPIKey.objects.filter(
            admin=request.user,
            service_name=service_name,
            active=True
        ).first()
        
        if not api_key:
            return Response({"error": "API key not found"}, status=404)
        
        api_key.active = False
        api_key.save()
        
        return Response({
            "success": True,
            "message": f"API key for {service_name} revoked"
        })

class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=400)

        try:
            admin = Admins.objects.get(email=email)
        except Admins.DoesNotExist:
            return Response({"error": "No admin account found with this email"}, status=404)

        # Generate reset token
        jwt_token = AccessToken.for_user(admin)
        jwt_token.set_exp(lifetime=timedelta(minutes=15))
        uidb64 = urlsafe_base64_encode(smart_bytes(admin.id))
        reset_link = f"http://127.0.0.1:8005/api/v1/reset-password/{uidb64}/{jwt_token}"

        # Send reset email via API Gateway
        try:
            response = requests.post(
                f"{settings.API_GATEWAY_URL}/api/v1/notifications/",
                json={
                    "user_id": str(admin.id),
                    "user_email": admin.email,
                    "template_code": "password_reset",
                    "variables": {
                        "name": admin.name,
                        "reset_link": reset_link
                    }
                },
                headers={"X-API-KEY": settings.ADMIN_API_KEY},
                timeout=10
            )
        except:
            return Response({"error": "Failed to send reset email"}, status=500)

        return Response({"message": "Password reset link sent to your email"}, status=200)

class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, uidb64, token):
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if new_password != confirm_password:
            return Response({"error": "Passwords do not match"}, status=400)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            admin = Admins.objects.get(id=uid)
        except Exception:
            return Response({"error": "Invalid reset link"}, status=400)

        try:
            decoded_token = AccessToken(token)
            if str(decoded_token['user_id']) != str(admin.id):
                return Response({"error": "Token does not belong to this admin."}, status=400)
        except TokenError:
            return Response({"error": "Invalid or expired token"}, status=400)

        admin.set_password(new_password)
        admin.save()

        return Response({"message": "Password has been reset successfully."}, status=200)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    return Response({
        "success": True,
        "message": "admin_service_healthy",
        "data": {"service": "admin_service"}
    })