from django.conf import settings
import firebase_admin
from firebase_admin import credentials, messaging
import os
import json
import logging


logger = logging.getLogger(__name__)

class PushService:
    def __init__(self):
        self.service_account_path = getattr(settings, 'FCM_SERVICE_ACCOUNT_KEY_PATH', os.getenv('FCM_SERVICE_ACCOUNT_KEY_PATH'))
        
        if not self.service_account_path:
            raise ValueError("FCM_SERVICE_ACCOUNT_KEY_PATH is required for push notifications")
        
        # Initialize Firebase Admin SDK
        if not firebase_admin._apps:
            cred = credentials.Certificate(self.service_account_path)
            firebase_admin.initialize_app(cred)
    
    def send_push(self, token, title, body, data=None):
        """Send push notification using Firebase Admin SDK"""
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                token=token
            )
            
            response = messaging.send(message)
            logger.info(f"Push sent successfully: {response}")
            return True, response, None
            
        except Exception as e:
            logger.error(f"FCM error: {e}")
            return False, None, str(e)