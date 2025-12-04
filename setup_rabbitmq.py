import pika
import sys

def setup_rabbitmq():
    # Setup RabbitMQ exchanges and queues
    try:
        # Connect to RabbitMQ
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        
        # Declare exchange
        channel.exchange_declare(
            exchange='notifications.direct',
            exchange_type='direct',
            durable=True
        )
        
        # Declare queues
        queues = [
            'email_notifications',
            'push_notifications', 
            'failed_notifications'
        ]
        
        for queue in queues:
            channel.queue_declare(queue=queue, durable=True)
            
        # Bind queues to exchange
        channel.queue_bind(
            exchange='notifications.direct',
            queue='email_notifications',
            routing_key='email'
        )
        
        channel.queue_bind(
            exchange='notifications.direct', 
            queue='push_notifications',
            routing_key='push'
        )
        
        channel.queue_bind(
            exchange='notifications.direct',
            queue='failed_notifications', 
            routing_key='failed'
        )
        
        print("RabbitMQ setup completed successfully!")
        print("Email_notifications queue ready")
        print("Push_notifications queue ready") 
        print("Failed_notifications queue ready")
        
        connection.close()
        
    except Exception as e:
        print(f"RabbitMQ setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_rabbitmq()

