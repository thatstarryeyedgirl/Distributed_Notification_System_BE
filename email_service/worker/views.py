from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from .models import EmailNotification
from .decorators import internal_service_required
from .serializers import EmailNotificationSerializer


@csrf_exempt
@require_GET
def health_check(request):
    # Health endpoint for monitoring
    return JsonResponse({
        "success": True,
        "message": "email_service_healthy",
        "data": {"service": "email_service"},
        "meta": {}
    })


@csrf_exempt
@internal_service_required
@require_GET
def notification_status(request, notification_id):
    # Check the delivery status of a notification
    try:
        notification = EmailNotification.objects.get(id=notification_id)
        serializer = EmailNotificationSerializer(notification)
        return JsonResponse({
            "success": True,
            "data": serializer.data,
            "message": "Notification status fetched successfully"
        })
    except EmailNotification.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Notification not found",
            "message": f"No notification found for ID {notification_id}"
        }, status=404)

