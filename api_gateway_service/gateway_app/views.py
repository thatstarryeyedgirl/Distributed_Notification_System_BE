import os
import json
import uuid
import logging
import requests

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils.decorators import method_decorator

from .models import NotificationRequest
from .serializers import NotificationRequestSerializer
from .rabbitmq_client import publish_to_queue
from .decorators import require_api_key


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

USER_SERVICE_URL = os.getenv('USER_SERVICE_URL')
API_GATEWAY_KEY = os.getenv('API_GATEWAY_KEY')


def call_user_service(user_id, retries=3):
    headers = {'X-API-KEY': API_GATEWAY_KEY}
    for attempt in range(retries):
        try:
            resp = requests.get(f"{USER_SERVICE_URL}/users/{user_id}/", headers=headers, timeout=5)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                return {"success": False, "error": "user_not_found"}
        except requests.RequestException as e:
            logger.warning(f"User service call failed (attempt {attempt+1}/{retries}): {e}")
    return {"success": False, "error": "user_service_unreachable"}


@method_decorator(require_api_key, name='dispatch')
class NotificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logger.info(f"Incoming notification request: {request.data}")
        data = request.data.copy()

        # Extract user info
        user_id = getattr(request.user, "user_id", request.user.id)
        data["user_id"] = str(user_id)
        data["user_name"] = getattr(request.user, "name", request.user.username)

        # Call user-service
        user_resp = call_user_service(data["user_id"])
        if not user_resp.get("success"):
            error = user_resp.get("error")
            msg_map = {
                "user_not_found": "User not found",
                "user_service_unreachable": "User service is unreachable"
            }
            return Response({
                "success": False,
                "error": error,
                "message": msg_map.get(error, "User service error")
            }, status=status.HTTP_404_NOT_FOUND if error=="user_not_found" else status.HTTP_503_SERVICE_UNAVAILABLE)

        user_info = user_resp.get("data", {})
        preferences = user_info.get("preferences", {})

        notification_type = data.get("notification_type")
        if notification_type == "email" and not preferences.get("email", False):
            return Response({
                "success": False,
                "error": "preference_disabled",
                "message": "User disabled email notifications",
            }, status=status.HTTP_400_BAD_REQUEST)

        if notification_type == "push" and not preferences.get("push", False):
            return Response({
                "success": False,
                "error": "preference_disabled",
                "message": "User disabled push notifications",
            }, status=status.HTTP_400_BAD_REQUEST)

        # Add user email or push token
        if notification_type == "email":
            data["user_email"] = user_info.get("email")
            data.pop("push_token", None)
        else:
            data["push_token"] = user_info.get("push_token")
            data.pop("user_email", None)

        # Generate request_id
        data.setdefault("request_id", f"req_{uuid.uuid4().hex[:6]}")

        # Idempotency check
        existing = NotificationRequest.objects.filter(request_id=data["request_id"]).first()
        if existing:
            return Response({
                "success": True,
                "message": "notification_already_exists",
                "data": NotificationRequestSerializer(existing).data,
            }, status=status.HTTP_200_OK)

        # Create notification
        serializer = NotificationRequestSerializer(data=data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "error": "invalid_payload",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        notification = serializer.save(status="queued")
        
        # Generate notification_id for tracking across services
        notification_id = f"{notification.notification_type}_{uuid.uuid4().hex[:8]}"
        
        # Prepare message data with notification_id
        message_data = NotificationRequestSerializer(notification).data
        message_data['notification_id'] = notification_id
        message_data['id'] = notification_id  # For backward compatibility

        # Publish to RabbitMQ with proper routing
        queue_name = f"{notification.notification_type}_notifications"
        if not publish_to_queue(queue_name, message_data):
            notification.status = "failed"
            notification.save(update_fields=["status"])
            return Response({
                'success': False,
                'error': 'queue_failed',
                'message': 'Failed to queue notification',
                'data': {},
                'meta': {}
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({
            'success': True,
            'message': 'notification_queued',
            'data': {'notification_id': notification_id, 'request_id': notification.request_id},
            'meta': {}
        }, status=status.HTTP_201_CREATED)


@csrf_exempt
@require_api_key
def enqueue_notification(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Only POST allowed'}, status=405)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    serializer = NotificationRequestSerializer(data=payload)
    if not serializer.is_valid():
        return JsonResponse({'error': 'invalid_payload', 'details': serializer.errors}, status=400)

    notification = serializer.save(status="queued")
    success = publish_to_queue(notification.notification_type, NotificationRequestSerializer(notification).data)
    if not success:
        notification.status = "failed"
        notification.save(update_fields=["status"])
        return JsonResponse({'error': 'Failed to queue'}, status=503)

    return JsonResponse({
        'status': 'queued',
        'request_id': notification.request_id
    })


@method_decorator(require_api_key, name='dispatch')
class HealthView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            'success': True,
            'message': 'gateway_service_healthy',
            'data': {'service': 'api_gateway_service'}
        })


