#!/bin/bash

# Distributed Notification System Deployment Script

set -e

echo "Starting deployment of Distributed Notification System..."

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "docker-compose is not installed"
    exit 1
fi

# Function to check service health
check_health() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo "Checking health of $service_name on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "http://localhost:$port/api/v1/health/" > /dev/null 2>&1; then
            echo "$service_name is healthy"
            return 0
        fi
        
        echo "Attempt $attempt/$max_attempts - $service_name not ready yet..."
        sleep 5
        ((attempt++))
    done
    
    echo "$service_name failed to become healthy"
    return 1
}

# Stop existing containers
echo "Stopping existing containers..."
docker-compose down --remove-orphans

# Pull latest images
echo "Pulling latest images..."
docker-compose pull

# Start infrastructure services first
echo "Starting infrastructure services..."
docker-compose up -d redis rabbitmq

# Wait for infrastructure to be ready
echo "Waiting for infrastructure services..."
sleep 15

# Setup RabbitMQ queues
echo "Setting up RabbitMQ queues..."
python setup_rabbitmq.py

# Start application services
echo "Starting application services..."
docker-compose up -d

# Wait for services to start
echo "Waiting for services to initialize..."
sleep 30

# Check health of all services
echo "Running health checks..."
check_health "API Gateway" 8000
check_health "User Service" 8001
check_health "Template Service" 8002
check_health "Email Service" 8003
check_health "Push Service" 8004
check_health "Admin Service" 8005

# Run system integration test
echo "Running integration tests..."
python test_system.py

echo "Deployment completed successfully!"
echo ""
echo "Service URLs:"
echo "  API Gateway:      http://localhost:8000"
echo "  User Service:     http://localhost:8001"
echo "  Template Service: http://localhost:8002"
echo "  Email Service:    http://localhost:8003"
echo "  Push Service:     http://localhost:8004"
echo "  Admin Service:    http://localhost:8005"
echo ""
echo "Management URLs:"
echo "RabbitMQ:         http://localhost:15672 (guest/guest)"
echo ""
echo "API Documentation:"
echo "  Swagger UI:       http://localhost:8000/docs/"
echo ""
echo "System is ready for use!"

