from django.contrib.auth import get_user_model
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken, TokenError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import smart_bytes, force_str
from datetime import timedelta
from .models import Users, NotificationLog, ErrorLog
from .serializers import UsersRegisterSerializer, UsersSerializer, DeviceSerializer, NotificationPreferenceSerializer, NotificationStatusSerializer
from django.db import IntegrityError
from django.conf import settings
from rest_framework.views import APIView
from .utils import publish_user_event
import uuid

User = get_user_model()


class UserRegisterView(generics.GenericAPIView):
    serializer_class = UsersRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        try:
            if not serializer.is_valid():
                return Response({
                    "success": False,
                    "error": "validation_error",
                    "message": "Invalid user data",
                    "data": serializer.errors,
                    "meta": {}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user = serializer.save()

            # Event-driven: publish user_registered event
            publish_user_event(user, event_type='user_registered')

            return Response({
                "success": True,
                "message": "user_created",
                "data": serializer.to_representation(user),
                "meta": {}
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            if isinstance(e, IntegrityError) and 'email' in str(e):
                return Response({
                    "success": False,
                    "error": "validation_error",
                    "message": "Invalid user data",
                    "data": {"email": ["User with this email already exists."]},
                    "meta": {}
                }, status=status.HTTP_400_BAD_REQUEST)
            return Response({
                "success": False,
                "error": "validation_error",
                "message": "Invalid user data",
                "data": {"error": [str(e)]},
                "meta": {}
            }, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        
        if not email or not password:
            return Response({"error": "email and password required"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = Users.objects.filter(email=email).first()
        
        if user is None:
            return Response({"error": "No account found with this email"}, status=status.HTTP_404_NOT_FOUND)
        
        if not user.check_password(password):
            return Response({"error": "Email or password incorrect"}, status=status.HTTP_401_UNAUTHORIZED)
        
        refresh = RefreshToken.for_user(user)
        data = {
            "user": UsersSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }
        return Response(data, status=status.HTTP_200_OK)


class InternalValidateTokenView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        # expect header X-INTERNAL-KEY with API_GATEWAY_KEY
        internal_key = request.headers.get('X-INTERNAL-KEY')
        if internal_key != settings.API_GATEWAY_KEY:
            return Response({"detail":"Unauthorized"}, status=401)

        token = request.data.get('token')
        if not token:
            return Response({"detail":"token required"}, status=400)
        try:
            at = AccessToken(token)
            user_id = at['user_id']
            user = Users.objects.filter(user_id=user_id).first()
            if not user:
                return Response({"detail":"invalid token: user not found"}, status=404)
            return Response({"success": True, "user": UsersSerializer(user).data}, status=200)
        except Exception as e:
            return Response({"detail":"invalid or expired token", "error": str(e)}, status=401)


class DeviceRegisterView(generics.CreateAPIView):
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        return Response(DeviceSerializer(device).data, status=status.HTTP_201_CREATED)


class PreferenceUpdateView(generics.UpdateAPIView):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        pref_obj = request.user.preferences
        email_pref = request.data.get("email")
        push_pref = request.data.get("push")

        if email_pref is not None:
            pref_obj.email = bool(email_pref)
        if push_pref is not None:
            pref_obj.push = bool(push_pref)

        pref_obj.save()
        return Response(NotificationPreferenceSerializer(pref_obj).data, status=200)


class ForgotPasswordView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=400)

        try:
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            return Response({"error": "No account found with this email"}, status=404)

        if user.preferences.email:
            jwt_token = AccessToken.for_user(user)
            jwt_token.set_exp(lifetime=timedelta(minutes=15))
            uidb64 = urlsafe_base64_encode(smart_bytes(user.user_id))
            reset_link = f"http://127.0.0.1:8001/api/v1/reset-password/{uidb64}/{jwt_token}"

            publish_user_event(user, event_type='password_reset_requested', extra_data={"reset_link": reset_link})

            return Response({"message": "Password reset link sent to your email"}, status=200)
        
        elif user.preferences.push:
            device = user.devices.first()
            if not device:
                return Response({"error": "No push token found for this user"}, status=400)
            
            # generate JWT for reset
            jwt_token = AccessToken.for_user(user)
            jwt_token.set_exp(lifetime=timedelta(minutes=15))
            password_reset_token = str(jwt_token)
            # log the notification
            log = NotificationLog.objects.create(
                notification_id=str(uuid.uuid4()),
                user=user,
                notification_preference='push',
                status='pending'
                )
            
            # publish event to push service
            publish_user_event(
                user=user,
                event_type="password_reset_push",
                device_token=device.push_token,
                extra_data={
                    "reset_token": password_reset_token,
                    "notification_id": log.notification_id
                    })
            return Response({
                "message": "Password reset push notification sent",
                "notification_id": log.notification_id
                }, status=200)


class ResetPasswordView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, uidb64, token):
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if new_password != confirm_password:
            return Response({"error": "Passwords do not match"}, status=400)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = Users.objects.get(user_id=uid)
        except Exception:
            return Response({"error": "Invalid reset link"}, status=400)

        try:
            decoded_token = AccessToken(token)
            if str(decoded_token['user_id']) != str(user.id):
                return Response({"error": "Token does not belong to this user."}, status=400)
        except TokenError:
            return Response({"error": "Invalid or expired token"}, status=400)

        user.set_password(new_password)
        user.save()

        return Response({"message": "Password has been reset successfully."}, status=200)


class UserDetailView(generics.RetrieveAPIView):
    serializer_class = UsersSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'user_id'
    
    def get_queryset(self):
        return Users.objects.all()
    
    def retrieve(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            return Response({
                "success": True,
                "message": "user_found",
                "data": self.get_serializer(user).data,
                "meta": {}
            }, status=200)
        except Users.DoesNotExist:
            return Response({
                "success": False,
                "error": "user_not_found",
                "message": "User does not exist",
                "data": {},
                "meta": {}
            }, status=404)


class NotificationStatusView(generics.GenericAPIView):
    serializer_class = NotificationStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, notification_preference):
        if notification_preference not in ['email', 'push']:
            return Response({"error": "Invalid notification preference"}, status=400)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        notification_id = serializer.validated_data['notification_id']
        try:
            notification_log = NotificationLog.objects.get(notification_id=notification_id)
            notification_log.status = serializer.validated_data['status']
            notification_log.save()

            if serializer.validated_data['status'] == 'failed':
                service_name = serializer.validated_data.get('service_name', f'{notification_preference}_service')
                error_code = serializer.validated_data.get('error_code', 'UNKNOWN_ERROR')
                error_message = serializer.validated_data.get('error_message', 'No error details provided')
                ErrorLog.objects.create(
                    notification=notification_log,
                    service_name=service_name,
                    error_code=error_code,
                    error_message=error_message
                )

            return Response({"message": "Status updated successfully"}, status=200)
        except NotificationLog.DoesNotExist:
            return Response({"error": "Notification not found"}, status=404)


class HealthView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request): 
        return Response({"status":"ok"}, status=200)

