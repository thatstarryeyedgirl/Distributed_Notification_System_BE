from django.core.management.base import BaseCommand
from worker.rabbitmq_consumer import EmailConsumer

class Command(BaseCommand):
    help = 'Start consuming email notifications from RabbitMQ'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting email consumer...'))
        consumer = EmailConsumer()
        consumer.start_consuming()