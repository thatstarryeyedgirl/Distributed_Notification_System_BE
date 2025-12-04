import requests
from django.conf import settings
from .models import EmailNotification
from .tasks import send_email_task
from .circuit_breaker import circuit_breaker
from .api_client import ServiceAPIClient


class EmailService:
    @classmethod
    def send_welcome_email(cls, user_id, user_email, user_name):
        return cls._create_notification(
            user_id=user_id,
            to_email=user_email,
            template_code=EmailNotification.TEMPLATE_WELCOME,
            variables={'user_name': user_name, 'app_name': 'NotificationApp'}
        )
    
    @classmethod
    def send_password_reset(cls, user_id, user_email, reset_link):
        return cls._create_notification(
            user_id=user_id,
            to_email=user_email,
            template_code=EmailNotification.TEMPLATE_PASSWORD_RESET,
            variables={'reset_link': reset_link}
        )
    
    @classmethod
    def send_email_verification(cls, user_id, user_email, verification_link):
        return cls._create_notification(
            user_id=user_id,
            to_email=user_email,
            template_code=EmailNotification.TEMPLATE_VERIFICATION,
            variables={'verification_link': verification_link}
        )
    
    @classmethod
    def _create_notification(cls, user_id, to_email, template_code, variables):
        # Verify user exists in user_service
        if not cls._verify_user_exists(user_id):
            raise ValueError(f"User {user_id} not found in user_service")
        
        notification = EmailNotification.objects.create(
            request_id=f"{template_code}_{user_id}_{hash(to_email)}",
            user_id=user_id,
            to_email=to_email,
            template_code=template_code,
            variables=variables
        )
        
        # Trigger async email sending
        send_email_task.delay(notification.id)
        
        return notification
    
    @classmethod
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=requests.RequestException)
    def _verify_user_exists(cls, user_id):
        try:
            user_exists, user_data = ServiceAPIClient.verify_user_exists(user_id)
            
            if not user_exists:
                error_msg = user_data.get('error', 'Unknown error')
                raise ValueError(f"User verification failed: {error_msg}")
            
            # Check if user has email preference enabled
            preferences = user_data.get('preferences', {})
            if not preferences.get('email', True):  # Default to True for development
                raise ValueError("Access denied: User has not enabled email notifications")

            return True
                
        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            print(f"User service request error: {e}")
            raise ValueError("User service unavailable - cannot verify user")


