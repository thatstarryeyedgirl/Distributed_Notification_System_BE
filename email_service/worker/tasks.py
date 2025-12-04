import os
import json
import logging
import pika
import time
import requests
from celery import Celery
from django.core.mail import send_mail
from django.conf import settings
from .models import EmailNotification, DeliveryLog
import uuid
from collections import defaultdict

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Celery initialization
app = Celery('email_service')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# RabbitMQ settings
RABBITMQ_URL = os.getenv('RABBITMQ_URL', settings.RABBITMQ_URL)
EXCHANGE_NAME = 'notifications.direct'
EMAIL_QUEUE = 'email.queue'
DEAD_LETTER_QUEUE = 'failed.queue'
ROUTING_KEY = "email"

# Template Service
TEMPLATE_SERVICE_URL = os.getenv('TEMPLATE_SERVICE_URL', settings.TEMPLATE_SERVICE_URL)
TEMPLATE_SERVICE_KEY = os.getenv('TEMPLATE_SERVICE_KEY', settings.TEMPLATE_SERVICE_KEY)


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


def consume_email_queue():
    connection = None
    try:
        connection = connect_rabbitmq()
        channel = connection.channel()

        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)
        channel.queue_declare(queue=EMAIL_QUEUE, durable=True)
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=EMAIL_QUEUE, routing_key=ROUTING_KEY)
        channel.queue_declare(queue=DEAD_LETTER_QUEUE, durable=True)

        def callback(ch, method, body):
            try:
                data = json.loads(body)
                request_id = data.get('request_id', str(uuid.uuid4()))
                notification = EmailNotification.objects.create(
                    request_id=request_id,
                    to_email=data.get('user_email') or data.get('to_email'),
                    user_id=data.get('user_id'),
                    template_code=data.get('template_code', 'default'),
                    variables=data.get('variables', {}),
                    priority=data.get('priority', 1),
                    metadata=data.get('metadata', {})
                )

                send_email_task.apply_async(args=[str(notification.id)], countdown=1)
                logger.info(f"Queued email task for {notification.to_email}, request_id={request_id}")
                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                logger.error(f"Failed to process message: {e}")
                channel.basic_publish(
                    exchange=EXCHANGE_NAME,
                    routing_key=DEAD_LETTER_QUEUE,
                    body=body
                )
                ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(queue=EMAIL_QUEUE, on_message_callback=callback)
        logger.info("Started consuming email queue...")
        channel.start_consuming()

    finally:
        if connection and not connection.is_closed:
            connection.close()


@app.task(bind=True, max_retries=5, default_retry_delay=60)
def send_email_task(self, notification_id):
    notification = None
    try:
        notification = EmailNotification.objects.get(id=notification_id)
        notification.status = EmailNotification.STATUS_PROCESSING
        notification.save()

        # Fetch template
        try:
            resp = requests.get(
                f"{TEMPLATE_SERVICE_URL}/templates/{notification.template_code}",
                headers={
                    "X-API-KEY": TEMPLATE_SERVICE_KEY
                },
                timeout=10
            )
            resp.raise_for_status()
            template_data = resp.json().get("data", {})
            subject_template = template_data.get("subject", "Notification")
            body_template = template_data.get("body", "You have a new notification.")
        except requests.RequestException as e:
            logger.error(f"Failed to fetch template {notification.template_code}: {e}")
            raise e

        # Safe substitution with defaultdict
        variables = notification.variables or {}
        subject = subject_template.format_map(defaultdict(str, variables))
        body = body_template.format_map(defaultdict(str, variables))

        # Send email
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.to_email],
                fail_silently=False
            )
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            raise e

        # Update notification and delivery log
        notification.auto_update_status('delivered')
        DeliveryLog.objects.create(
            notification=notification,
            status=DeliveryLog.STATUS_DELIVERED,
            message_id=f"msg_{notification.id}",
            provider_response={'smtp_status': 'sent'}
        )
        logger.info(f"Email sent successfully to {notification.to_email}, request_id={notification.request_id}")

    except Exception as exc:
        logger.error(f"Email sending failed for notification_id={notification_id}: {exc}")
        if notification:
            notification.attempts += 1
            notification.auto_update_status('failed', str(exc))
            notification.save()
        countdown = min(2 ** self.request.retries * 60, 3600)
        raise self.retry(exc=exc, countdown=countdown)


