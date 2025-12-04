import json
import logging
import pika
from uuid import UUID
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from .models import Users
from contextlib import contextmanager
from time import sleep

logger = logging.getLogger(__name__)

EXCHANGE_NAME = 'notifications.direct'
EMAIL_QUEUE = 'email.queue'
PUSH_QUEUE = 'push.queue'
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds


# Context manager to reuse RabbitMQ connection/channel safely
@contextmanager
def rabbitmq_connection():
    connection = None
    try:
        connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URL))
        channel = connection.channel()
        # Declare exchange and queues
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)
        channel.queue_declare(queue=EMAIL_QUEUE, durable=True)
        channel.queue_declare(queue=PUSH_QUEUE, durable=True)
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=EMAIL_QUEUE, routing_key=EMAIL_QUEUE)
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=PUSH_QUEUE, routing_key=PUSH_QUEUE)
        yield channel
    except Exception as e:
        logger.error(f"RabbitMQ connection failed: {e}")
        raise
    finally:
        if connection and not connection.is_closed:
            connection.close()


def publish_user_event(user: Users, event_type: str, extra_data: dict | None = None) -> bool:
    if not user:
        logger.error("Invalid user object for publishing event.")
        return False

    preference = "email" if user.preferences.email else "push"
    device_token = None

    if preference == "push":
        device = user.devices.first()
        if device:
            device_token = device.push_token

    event_payload = {
        "event_type": event_type,
        "user": {
            "user_id": str(user.user_id),
            "email": user.email,
            "name": user.name,
            "preference": preference,
        },
        "extra_data": extra_data or {}
    }

    if device_token:
        event_payload["extra_data"]["device_token"] = device_token

    for attempt in range(RETRY_ATTEMPTS):
        try:
            with rabbitmq_connection() as channel:
                routing_key = EMAIL_QUEUE if preference == "email" else PUSH_QUEUE
                channel.basic_publish(
                    exchange=EXCHANGE_NAME,
                    routing_key=routing_key,
                    body=json.dumps(event_payload),
                    properties=pika.BasicProperties(delivery_mode=2)  # Persistent message
                )
                logger.info(f"Published '{event_type}' event for {user.email}")
                return True
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed to publish '{event_type}': {e}")
            sleep(RETRY_DELAY)
    logger.error(f"All retry attempts failed for publishing '{event_type}' event for {user.email}")
    return False


def send_welcome_email(user: Users) -> bool:
    # Shortcut to publish a user_registered event.
    return publish_user_event(user, event_type="user_registered")


def update_user_name(user_uuid_str: str, new_name: str):
    try:
        user_uuid = UUID(user_uuid_str)
        user = Users.objects.get(user_id=user_uuid)
        user.name = new_name
        user.save()
        return f"User {user.email} updated successfully."
    except ValueError:
        logger.error(f"Invalid UUID format: {user_uuid_str}")
        return "Invalid UUID format."
    except ObjectDoesNotExist:
        logger.error(f"User not found: {user_uuid_str}")
        return "User not found."


