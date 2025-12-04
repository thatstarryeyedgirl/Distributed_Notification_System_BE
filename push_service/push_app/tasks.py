import os
import json
import logging
import pika
import time
from celery import Celery
from django.conf import settings
from .models import PushNotification
import uuid
from pyfcm import FCMNotification

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Celery('push_service')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# RabbitMQ settings
RABBITMQ_URL = os.getenv('RABBITMQ_URL', settings.RABBITMQ_URL)
EXCHANGE_NAME = 'notifications.direct'
PUSH_QUEUE = 'push.queue'
DEAD_LETTER_QUEUE = 'failed.queue'
ROUTING_KEY = 'push'


def connect_rabbitmq(retry_delay=5, max_retries=5):
    for attempt in range(max_retries):
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(params)
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ connection failed: {e}, retrying in {retry_delay}s...")
            time.sleep(retry_delay)
    raise ConnectionError("Failed to connect to RabbitMQ after multiple attempts.")


def consume_push_queue():
    connection = None
    try:
        connection = connect_rabbitmq()
        channel = connection.channel()

        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)
        channel.queue_declare(queue=PUSH_QUEUE, durable=True)
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=PUSH_QUEUE, routing_key=ROUTING_KEY)
        channel.queue_declare(queue=DEAD_LETTER_QUEUE, durable=True)

        def callback(ch, method, body):
            try:
                data = json.loads(body)
                notification = PushNotification.objects.create(
                    request_id=data.get('request_id', str(uuid.uuid4())),
                    to_device_token=data.get('device_token'),
                    template_code=data.get('template_code', 'default'),
                    variables=data.get('variables', {}),
                    priority=data.get('priority', 1),
                    metadata=data.get('metadata', {}),
                )

                send_push_task.apply_async(args=[str(notification.id)], countdown=1)
                logger.info(f"Queued push task for {notification.to_device_token}")

                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                logger.error(f"Failed to process push message: {e}")
                channel.basic_publish(
                    exchange=EXCHANGE_NAME,
                    routing_key=DEAD_LETTER_QUEUE,
                    body=body
                )
                ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(queue=PUSH_QUEUE, on_message_callback=callback)
        logger.info("Started consuming push queue...")
        channel.start_consuming()

    finally:
        if connection and not connection.is_closed:
            connection.close()


@app.task(bind=True, max_retries=5, default_retry_delay=60)
def send_push_task(self, notification_id):
    notification = None
    try:
        # Fetch notification
        notification = PushNotification.objects.get(id=notification_id)
        notification.status = PushNotification.STATUS_PROCESSING
        notification.save()

        # Extract device token and variables
        device_token = notification.to_device_token
        variables = notification.variables or {}
        message_title = variables.get('title', 'Notification')
        message_body = variables.get('body', 'You have a new notification.')
        message_image = variables.get('image')
        click_action = variables.get('click_action')
        data_payload = variables.get('data', {})

        # Basic device token validation
        if not device_token or not isinstance(device_token, str) or len(device_token) < 20:
            raise ValueError(f"Invalid device token: {device_token}")

        # Initialize FCM client
        push_service = FCMNotification(api_key=settings.FCM_SERVER_KEY)

        # Send push notification
        result = push_service.notify_single_device(
            registration_id=device_token,
            message_title=message_title,
            message_body=message_body,
            data_message=data_payload,
            sound=variables.get('sound', 'default'),
            badge=variables.get('badge', 1),
            click_action=click_action,
            image=message_image
        )

        # Handle result
        if result.get('failure', 0) > 0:
            raise Exception(f"FCM failed: {result}")

        # Mark notification delivered
        notification.status = PushNotification.STATUS_DELIVERED
        notification.save()
        logger.info(f"Push sent successfully to {device_token}")

    except Exception as exc:
        logger.error(f"Push sending failed for {notification_id}: {exc}")
        if notification:
            notification.attempts += 1
            notification.status = PushNotification.STATUS_FAILED
            notification.save()

        # Retry with exponential backoff
        countdown = min(2 ** self.request.retries * 60, 3600)
        raise self.retry(exc=exc, countdown=countdown)



