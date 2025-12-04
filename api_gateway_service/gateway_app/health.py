from django.http import JsonResponse
from django.db import connection
import pika
import redis
import os

def health_check(request):
    health_status = {
        "success": True,
        "message": "api_gateway_service_healthy",
        "data": {
            "service": "api_gateway_service",
            "version": "1.0.0",
            "timestamp": "2024-01-01T00:00:00Z"
        },
        "meta": {
            "total": 0,
            "limit": 0,
            "page": 0,
            "total_pages": 0,
            "has_next": False,
            "has_previous": False
        }
    }
    
    checks = {}
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
        health_status["success"] = False
    
    # RabbitMQ check
    try:
        rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
        connection_params = pika.URLParameters(rabbitmq_url)
        conn = pika.BlockingConnection(connection_params)
        conn.close()
        checks["rabbitmq"] = "healthy"
    except Exception as e:
        checks["rabbitmq"] = f"unhealthy: {str(e)}"
        health_status["success"] = False
    
    # Redis check
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        r.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
        health_status["success"] = False
    
    health_status["data"]["checks"] = checks
    
    status_code = 200 if health_status["success"] else 503
    return JsonResponse(health_status, status=status_code)