import os
import requests
from django.conf import settings
from typing import Dict, Optional

class ServiceAPIClient:
    # Handles API calls to other services with proper authentication
    
    # API keys for calling other services (what THEY expect from us)
    SERVICE_KEYS = {
        'user_service': os.getenv('EMAIL_SERVICE_KEY', 'email_key_12345'),  # User service expects this from email service
        'template_service': os.getenv('EMAIL_SERVICE_KEY', 'email_key_12345'),  # Template service expects this from email service
        'admin_service': os.getenv('EMAIL_SERVICE_KEY', 'email_key_12345')  # Admin service expects this from email service
    }
    
    # Service URLs
    SERVICE_URLS = {
        'user_service': os.getenv('USER_SERVICE_URL', 'http://user_service:8001'),
        'template_service': os.getenv('TEMPLATE_SERVICE_URL', 'http://template_service:8002'),
        'admin_service': os.getenv('ADMIN_SERVICE_URL', 'http://admin_service:8005')
    }
    
    @classmethod
    def get_headers_for_service(cls, service_name: str) -> Dict[str, str]:
        # Get authentication headers for calling a specific service
        api_key = cls.SERVICE_KEYS.get(service_name)
        if not api_key:
            raise ValueError(f"No API key configured for service: {service_name}")
        
        return {
            'X-API-KEY': api_key,
            'X-Calling-Service': 'email_service',
            'Content-Type': 'application/json'
        }
    
    @classmethod
    def call_user_service(cls, endpoint: str, method: str = 'GET', data: dict = None) -> requests.Response:
        # Make authenticated call to user service
        url = f"{cls.SERVICE_URLS['user_service']}{endpoint}"
        headers = cls.get_headers_for_service('user_service')
        
        if method.upper() == 'GET':
            return requests.get(url, headers=headers, timeout=10)
        elif method.upper() == 'POST':
            return requests.post(url, headers=headers, json=data, timeout=10)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    
    @classmethod
    def call_template_service(cls, endpoint: str, method: str = 'GET', data: dict = None) -> requests.Response:
        # Make authenticated call to template service
        url = f"{cls.SERVICE_URLS['template_service']}{endpoint}"
        headers = cls.get_headers_for_service('template_service')
        
        if method.upper() == 'GET':
            return requests.get(url, headers=headers, timeout=10)
        elif method.upper() == 'POST':
            return requests.post(url, headers=headers, json=data, timeout=10)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    
    @classmethod
    def verify_user_exists(cls, user_id: str) -> tuple[bool, dict]:
        # Verify user exists and get user data
        try:
            response = cls.call_user_service(f"/api/v1/users/{user_id}/")
            
            if response.status_code == 200:
                user_data = response.json()
                if user_data.get('success'):
                    return True, user_data.get('data', {})
                else:
                    return False, {"error": "Invalid user data from user_service"}
            elif response.status_code == 404:
                return False, {"error": f"User {user_id} not found"}
            else:
                return False, {"error": f"User service returned status {response.status_code}"}
                
        except requests.exceptions.ConnectionError:
            return False, {"error": "User service unavailable"}
        except Exception as e:
            return False, {"error": f"User service request failed: {str(e)}"}
    
    @classmethod
    def get_email_template(cls, template_code: str) -> tuple[bool, dict]:
        # Get email template from template service
        try:
            response = cls.call_template_service(f"/api/v1/templates/{template_code}/")
            
            if response.status_code == 200:
                template_data = response.json()
                return True, template_data
            else:
                return False, {"error": f"Template service returned status {response.status_code}"}
                
        except requests.exceptions.ConnectionError:
            return False, {"error": "Template service unavailable"}
        except Exception as e:
            return False, {"error": f"Template service request failed: {str(e)}"}

