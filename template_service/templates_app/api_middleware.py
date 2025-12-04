import os
from django.http import JsonResponse

class APIKeyAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Map of which services are allowed to call us and their API keys
        self.authorized_services = {
            'api_gateway_service': os.getenv('API_GATEWAY_SERVICE_KEY', 'gw_key_12345'),
            'email_service': os.getenv('EMAIL_SERVICE_KEY', 'email_key_12345'),
            'push_service': os.getenv('PUSH_SERVICE_KEY', 'push_key_12345'),
            'admin_service': os.getenv('ADMIN_SERVICE_KEY', 'admin_key_12345'),
            'user_service': os.getenv('USER_SERVICE_KEY', 'user_key_12345')
        }
    
    def __call__(self, request):
        # Check if this is an internal service request
        calling_service = request.headers.get('X-Calling-Service')
        provided_api_key = request.headers.get('X-API-KEY')
        
        if calling_service and provided_api_key:
            # Check if the calling service is authorized
            if calling_service not in self.authorized_services:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "unauthorized", 
                        "message": f"Service '{calling_service}' is not authorized to access template service"
                    }, 
                    status=401
                )
            
            # Validate the API key matches the calling service
            expected_key = self.authorized_services[calling_service]
            if provided_api_key != expected_key or not expected_key:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "unauthorized", 
                        "message": f"Invalid API key for service '{calling_service}'"
                    }, 
                    status=401
                )
            
            # Add calling service info to request for logging
            request.calling_service = calling_service
            print(f"Authorized request from {calling_service} to template service")
        
        response = self.get_response(request)
        return response

