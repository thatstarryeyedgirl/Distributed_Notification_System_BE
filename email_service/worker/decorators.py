import os
import logging
from functools import wraps
from django.http import JsonResponse

logger = logging.getLogger(__name__)

SERVICE_API_KEYS = {
    'api_gateway_service': os.environ.get('API_GATEWAY_SERVICE_KEY'),
    'template_service': os.environ.get('TEMPLATE_SERVICE_API_KEY'),
    'user_service': os.environ.get('USER_SERVICE_API_KEY'),
}

def internal_service_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        service_name = request.headers.get("X-Service-Name")
        service_key = request.headers.get("X-Service-Key")

        if not service_name or not service_key:
            logger.warning("Missing internal service headers")
            return JsonResponse({"error": "Missing internal headers"}, status=403)

        expected_key = os.environ.get(f"{service_name.upper()}_API_KEY")


        if expected_key is None:
            logger.warning(f"Unauthorized service attempted access: {service_name}")
            return JsonResponse({"error": "Unauthorized service"}, status=403)

        if service_key != expected_key:
            logger.warning(f"Invalid API key for service: {service_name}")
            return JsonResponse({"error": "Unauthorized"}, status=403)

        logger.info(f"Internal request validated from {service_name}")
        return view_func(request, *args, **kwargs)

    return wrapper

