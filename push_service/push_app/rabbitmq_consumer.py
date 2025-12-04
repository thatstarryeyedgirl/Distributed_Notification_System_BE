import os
import json
import pika
import logging
import requests
from django.conf import settings
from .models import PushNotification, PushDeliveryLog
from .services import PushService

logger = logging.getLogger(__name__)

class PushConsumer:
    def __init__(self):
        self.rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
        self.exchange_name = 'notifications.direct'
        self.queue_name = 'push.queue'
        self.template_service_url = os.getenv('TEMPLATE_SERVICE_URL', 'http://localhost:8002/api/v1')
        self.user_service_url = os.getenv('USER_SERVICE_URL', 'http://localhost:8001/api/v1')
        
    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            params = pika.URLParameters(self.rabbitmq_url)
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()
            
            # Declare exchange and queue
            self.channel.exchange_declare(exchange=self.exchange_name, exchange_type='direct', durable=True)
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            self.channel.queue_bind(exchange=self.exchange_name, queue=self.queue_name, routing_key='push.queue')
            
            logger.info("Connected to RabbitMQ for push processing")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def process_message(self, ch, method, properties, body):
        """Process incoming push notification message"""
        try:
            # Parse message
            message = json.loads(body)
            logger.info(f"Processing push notification: {message}")
            
            # Create PushNotification record
            notification = PushNotification.objects.create(
                notification_id=message.get('id', f"push_{message['request_id']}"),
                request_id=message['request_id'],
                user_id=message['user_id'],
                push_token=message['push_token'],
                template_code=message['template_code'],
                variables=message['variables'],
                priority=message.get('priority', 1),
                metadata=message.get('metadata', {}),
                status=PushNotification.STATUS_PROCESSING
            )
            
            # Get processed template from Template Service
            processed_template = self.substitute_template_variables(
                message['template_code'], 
                message['variables'],
                message.get('language', 'en')
            )
            
            if not processed_template:
                self.handle_failure(notification, "Template processing failed")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Update notification with processed content
            notification.processed_title = processed_template.get('subject', 'Notification')
            notification.processed_body = processed_template['body']
            notification.save()
            
            # Send push notification
            push_service = PushService()
            success, message_id, error = push_service.send_push(
                token=notification.push_token,
                title=notification.processed_title,
                body=notification.processed_body,
                data=message.get('metadata', {})
            )
            
            if success:
                # Update status to delivered
                notification.status = PushNotification.STATUS_DELIVERED
                notification.save()
                
                # Log delivery
                PushDeliveryLog.objects.create(
                    notification=notification,
                    status='delivered',
                    fcm_message_id=message_id
                )
                
                # Report status back to User Service
                self.report_status(notification.notification_id, 'delivered')
                
                logger.info(f"Push sent successfully: {notification.notification_id}")
            else:
                self.handle_failure(notification, error)
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Error processing push message: {e}")
            # Reject and requeue for retry
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def substitute_template_variables(self, template_code, variables, language='en'):
        """Get processed template with variables substituted"""
        try:
            response = requests.post(f"{self.template_service_url}/templates/substitute/", 
                                   json={
                                       'template_code': template_code,
                                       'language': language,
                                       'variables': variables
                                   })
            if response.status_code == 200:
                return response.json().get('data')
            return None
        except Exception as e:
            logger.error(f"Failed to substitute template variables: {e}")
            return None
    
    def handle_failure(self, notification, error_message):
        """Handle push sending failure with retry logic"""
        notification.retry_count += 1
        notification.last_error = error_message
        
        if notification.retry_count >= notification.max_retries:
            notification.status = PushNotification.STATUS_FAILED
            # Report failure to User Service
            self.report_status(notification.notification_id, 'failed', error_message)
        else:
            notification.status = PushNotification.STATUS_PENDING
        
        notification.save()
        
        # Log failure
        PushDeliveryLog.objects.create(
            notification=notification,
            status='failed',
            fcm_response={'error': error_message},
            error_code='SEND_FAILED'
        )
        
        logger.error(f"Push sending failed: {notification.notification_id} - {error_message}")
    
    def report_status(self, notification_id, status, error=None):
        """Report delivery status back to User Service"""
        try:
            data = {
                'notification_id': notification_id,
                'status': status,
                'service_name': 'push_service',
                'error_code': 'PUSH_SEND_FAILED' if error else None,
                'error_message': error
            }
            
            response = requests.post(f"{self.user_service_url}/push/status/", json=data)
            if response.status_code == 200:
                logger.info(f"Status reported successfully: {notification_id} - {status}")
            else:
                logger.error(f"Failed to report status: {response.text}")
        except Exception as e:
            logger.error(f"Error reporting status: {e}")
    
    def start_consuming(self):
        """Start consuming messages from the queue"""
        if not self.connect():
            return
        
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=self.process_message)
        
        logger.info("Starting push consumer...")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Stopping push consumer...")
            self.channel.stop_consuming()
            self.connection.close()