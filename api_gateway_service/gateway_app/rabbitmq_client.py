import os
import json
import pika
import logging
from threading import Lock
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

RABBITMQ_URL = os.getenv('RABBITMQ_URL')
EXCHANGE_NAME = 'notifications.direct'
QUEUE_MAPPING = {
    'email_notifications': 'email_notifications',
    'push_notifications': 'push_notifications',
    'email': 'email_notifications',
    'push': 'push_notifications'
}

# Use a lock for thread-safe connection handling
_connection_lock = Lock()
_connection = None
_channel = None


def _connect():
    global _connection, _channel
    try:
        params = pika.URLParameters(RABBITMQ_URL)
        _connection = pika.BlockingConnection(params)
        _channel = _connection.channel()

        # Declare exchange
        _channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)

        # Declare queues and bind
        for key, queue_name in QUEUE_MAPPING.items():
            _channel.queue_declare(queue=queue_name, durable=True)
            _channel.queue_bind(queue=queue_name, exchange=EXCHANGE_NAME, routing_key=key)

        logger.info("Connected to RabbitMQ, exchange and queues declared.")
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        _connection, _channel = None, None
        raise


def get_connection_and_channel():
    global _connection, _channel
    with _connection_lock:
        if (_connection is None or _connection.is_closed) or (_channel is None or _channel.is_closed):
            _connect()
        return _connection, _channel


def publish_to_queue(notification_type, message, retries=3, delay=2):
    for attempt in range(1, retries + 1):
        try:
            _, channel = get_connection_and_channel()
            routing_key = QUEUE_MAPPING.get(notification_type)
            if not routing_key:
                logger.error(f"Unknown notification_type: {notification_type}")
                return False

            channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )
            logger.info(f"Published message to {routing_key} on attempt {attempt}")
            return True

        except (pika.exceptions.AMQPConnectionError, pika.exceptions.ChannelWrongStateError) as e:
            logger.warning(f"Attempt {attempt} failed due to connection/channel error: {e}")
            # Force reconnect on next attempt
            global _connection, _channel
            _connection, _channel = None, None

        except Exception as e:
            logger.error(f"Attempt {attempt} failed to publish: {e}")
            # Force reconnect on next attempt
            _connection, _channel = None, None

        # Delay before next retry
        if attempt < retries:
            time.sleep(delay)
        else:
            logger.error("All retry attempts failed")
            return False

