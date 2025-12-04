import os
import json
import pika
import logging
import requests
from django.conf import settings
from .models import EmailNotification, DeliveryLog
from .services import EmailService

logger = logging.getLogger(__name__)

class EmailConsumer:
    def __init__(self):
        self.rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
        self.exchange_name = 'notifications.direct'
        self.queue_name = 'email.queue'
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
            self.channel.queue_bind(exchange=self.exchange_name, queue=self.queue_name, routing_key='email.queue')
            
            logger.info("Connected to RabbitMQ for email processing")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def process_message(self, ch, method, properties, body):
        """Process incoming email notification message"""
        try:
            # Parse message
            message = json.loads(body)
            logger.info(f"Processing email notification: {message}")
            
            # Create EmailNotification record
            notification = EmailNotification.objects.create(
                notification_id=message.get('id', f"email_{message['request_id']}"),
                request_id=message['request_id'],
                user_id=message['user_id'],
                user_email=message['user_email'],
                template_code=message['template_code'],
                variables=message['variables'],
                priority=message.get('priority', 1),
                metadata=message.get('metadata', {}),
                status=EmailNotification.STATUS_PROCESSING
            )
            
            # Get template from Template Service
            template_data = self.get_template(message['template_code'], message.get('language', 'en'))
            if not template_data:
                self.handle_failure(notification, "Template not found")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Substitute variables
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
            notification.processed_subject = processed_template['subject']
            notification.processed_body = processed_template['body']
            notification.save()
            
            # Send email
            email_service = EmailService()
            success, message_id, error = email_service.send_email(
                to_email=notification.user_email,
                subject=notification.processed_subject,
                body=notification.processed_body
            )
            
            if success:
                # Update status to delivered
                notification.status = EmailNotification.STATUS_DELIVERED
                notification.save()
                
                # Log delivery
                DeliveryLog.objects.create(
                    notification=notification,
                    status='delivered',
                    message_id=message_id
                )
                
                # Report status back to User Service
                self.report_status(notification.notification_id, 'delivered')
                
                logger.info(f"Email sent successfully: {notification.notification_id}")
            else:
                self.handle_failure(notification, error)
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Error processing email message: {e}")
            # Reject and requeue for retry
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def get_template(self, template_code, language='en'):
        """Get template from Template Service"""
        try:
            response = requests.get(f"{self.template_service_url}/templates/{template_code}/", 
                                  params={'language': language})
            if response.status_code == 200:
                return response.json().get('data')
            return None
        except Exception as e:
            logger.error(f"Failed to get template: {e}")
            return None
    
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
        """Handle email sending failure with retry logic"""
        notification.retry_count += 1
        notification.last_error = error_message
        
        if notification.retry_count >= notification.max_retries:
            notification.status = EmailNotification.STATUS_FAILED
            # Report failure to User Service
            self.report_status(notification.notification_id, 'failed', error_message)
        else:
            notification.status = EmailNotification.STATUS_PENDING
        
        notification.save()
        
        # Log failure
        DeliveryLog.objects.create(
            notification=notification,
            status='failed',
            smtp_response=error_message,
            error_code='SEND_FAILED'
        )
        
        logger.error(f"Email sending failed: {notification.notification_id} - {error_message}")
    
    def report_status(self, notification_id, status, error=None):
        """Report delivery status back to User Service"""
        try:
            data = {
                'notification_id': notification_id,
                'status': status,
                'service_name': 'email_service',
                'error_code': 'EMAIL_SEND_FAILED' if error else None,
                'error_message': error
            }
            
            response = requests.post(f"{self.user_service_url}/email/status/", json=data)
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
        
        logger.info("Starting email consumer...")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Stopping email consumer...")
            self.channel.stop_consuming()
            self.connection.close()