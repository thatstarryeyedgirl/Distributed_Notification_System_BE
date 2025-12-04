import os
from django.http import JsonResponse
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Load API keys from environment variables
SERVICE_KEYS = {
    'user_service_api_key': os.getenv('USER_SERVICE_API_KEY'),
    'email_service_api_key': os.getenv('EMAIL_SERVICE_API_KEY'),
    'push_service_api_key': os.getenv('PUSH_SERVICE_API_KEY'),
    'api_gateway_service_key': os.getenv('API_GATEWAY_SERVICE_KEY'),
    'template_service_api_key': os.getenv('TEMPLATE_SERVICE_API_KEY')
}


def require_api_key(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        key = request.headers.get('x-api-key') or request.headers.get('X-API-KEY')

        if not key or key not in SERVICE_KEYS.values():
            logger.warning(f"Unauthorized request from IP {request.META.get('REMOTE_ADDR')}")
            return JsonResponse({'error': 'Invalid or missing API key'}, status=403)

        # Optionally, attach the service name to request for logging
        service_name = next((name for name, k in SERVICE_KEYS.items() if k == key), "unknown")
        request.service_name = service_name
        logger.info(f"Request authenticated from {service_name}")

        return view_func(request, *args, **kwargs)
    return _wrapped_view


