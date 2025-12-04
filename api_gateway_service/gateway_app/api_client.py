import os
import requests
from django.conf import settings
from typing import Dict, Optional

class ServiceAPIClient:
    """Handles API calls to other services with proper authentication"""
    
    # Service API keys - what we use to call other services
    SERVICE_KEYS = {
        'user_service': os.getenv('USER_SERVICE_KEY', ''),
        'template_service': os.getenv('TEMPLATE_SERVICE_KEY', ''),
        'email_service': os.getenv('EMAIL_SERVICE_KEY', ''),
        'push_service': os.getenv('PUSH_SERVICE_KEY', ''),
        'admin_service': os.getenv('ADMIN_SERVICE_KEY', '')
    }
    
    # Service URLs
    SERVICE_URLS = {
        'user_service': os.getenv('USER_SERVICE_URL', 'http://user_service:8001'),
        'template_service': os.getenv('TEMPLATE_SERVICE_URL', 'http://template_service:8002'),
        'email_service': os.getenv('EMAIL_SERVICE_URL', 'http://email_service:8003'),
        'push_service': os.getenv('PUSH_SERVICE_URL', 'http://push_service:8004'),
        'admin_service': os.getenv('ADMIN_SERVICE_URL', 'http://admin_service:8005')
    }
    
    @classmethod
    def get_headers_for_service(cls, service_name: str) -> Dict[str, str]:
        """Get authentication headers for calling a specific service"""
        api_key = cls.SERVICE_KEYS.get(service_name)
        if not api_key:
            raise ValueError(f"No API key configured for service: {service_name}")
        
        return {
            'X-API-KEY': api_key,
            'X-Calling-Service': 'api_gateway_service',
            'Content-Type': 'application/json'
        }
    
    @classmethod
    def validate_user_token(cls, token: str) -> tuple[bool, dict]:
        """Validate JWT token with user service"""
        try:
            headers = cls.get_headers_for_service('user_service')
            headers['X-Internal-Key'] = os.getenv('API_GATEWAY_KEY', '')  # Legacy header
            
            response = requests.post(
                f"{cls.SERVICE_URLS['user_service']}/api/v1/internal/validate-token/",
                headers=headers,
                json={'token': token},
                timeout=10
            )
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, {"error": f"Token validation failed: {response.status_code}"}
                
        except Exception as e:
            return False, {"error": f"User service request failed: {str(e)}"}
    
    @classmethod
    def send_notification_to_service(cls, service_name: str, notification_data: dict) -> tuple[bool, dict]:
        """Send notification to email or push service"""
        try:
            headers = cls.get_headers_for_service(service_name)
            
            response = requests.post(
                f"{cls.SERVICE_URLS[service_name]}/api/v1/notifications/",
                headers=headers,
                json=notification_data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                return True, response.json()
            else:
                return False, {"error": f"{service_name} returned status {response.status_code}"}
                
        except Exception as e:
            return False, {"error": f"{service_name} request failed: {str(e)}"}