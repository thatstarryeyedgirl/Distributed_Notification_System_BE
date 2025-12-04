from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from .models import PushNotification
from .decorators import internal_service_required
from .serializers import PushNotificationSerializer


@csrf_exempt
@require_GET
def health_check(request):
    return JsonResponse({
        "success": True,
        "message": "push_service_healthy",
        "data": {"service": "push_service"},
        "meta": {}
    })


@csrf_exempt
@internal_service_required
@require_GET
def notification_status(request, notification_id):
    try:
        notification = PushNotification.objects.get(id=notification_id)
        
        serialized = PushNotificationSerializer(notification).data

        return JsonResponse({
            "success": True,
            "data": serialized,
            "message": "Notification status fetched successfully"
        })

    except PushNotification.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Notification not found",
            "message": f"No notification found for ID {notification_id}"
        }, status=404)


