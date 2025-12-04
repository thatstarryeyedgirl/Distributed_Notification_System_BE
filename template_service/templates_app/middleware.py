from django.http import JsonResponse
from django.conf import settings

class APIKeyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip API key check for health endpoints
        if request.path.endswith('/health/'):
            return self.get_response(request)
        
        # Check for API key in headers
        api_key = request.headers.get('X-API-KEY')
        if not api_key:
            return JsonResponse({'error': 'API key required'}, status=401)
        
        # Only allow services that need to access Template Service
        valid_keys = [
            settings.EMAIL_SERVICE_KEY,  # Gets email templates
            settings.PUSH_SERVICE_KEY    # Gets push templates
        ]
        
        if api_key not in valid_keys:
            return JsonResponse({'error': 'Invalid API key'}, status=401)
        
        return self.get_response(request)