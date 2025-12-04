from django.core.management.base import BaseCommand
import pika
import json
import logging
from worker.models import EmailNotification

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Consume failed messages from dead letter queue'

    def handle(self, *args, **options):
        connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
        channel = connection.channel()
        
        # Declare dead letter queue
        channel.queue_declare(queue='failed.queue', durable=True)
        
        def callback(ch, method, properties, body):
            try:
                data = json.loads(body)
                logger.error(f"Processing failed message: {data}")
                
                # Mark notification as permanently failed
                if 'request_id' in data:
                    try:
                        notification = EmailNotification.objects.get(request_id=data['request_id'])
                        notification.status = EmailNotification.STATUS_FAILED
                        notification.error_message = "Moved to dead letter queue after max retries"
                        notification.save()
                    except EmailNotification.DoesNotExist:
                        logger.error(f"Notification not found for request_id: {data['request_id']}")
                
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
            except Exception as e:
                logger.error(f"Failed to process dead letter message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        
        channel.basic_consume(queue='failed.queue', on_message_callback=callback)
        self.stdout.write("Starting to consume failed queue...")
        channel.start_consuming()