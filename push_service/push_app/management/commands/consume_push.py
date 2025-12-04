from django.core.management.base import BaseCommand
from push_app.rabbitmq_consumer import PushConsumer

class Command(BaseCommand):
    help = 'Start consuming push notifications from RabbitMQ'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting push consumer...'))
        consumer = PushConsumer()
        consumer.start_consuming()