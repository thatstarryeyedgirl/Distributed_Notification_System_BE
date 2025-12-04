# Deployment Guide

## CI/CD Pipeline

The project includes a comprehensive CI/CD pipeline with the following stages:

### 1. Test Stage
- Runs unit tests for all 6 microservices
- Uses PostgreSQL, RabbitMQ, and Redis test services
- Validates database migrations
- Ensures code quality

### 2. Build Stage
- Builds Docker images for all services
- Pushes to GitHub Container Registry
- Supports multi-platform builds (AMD64/ARM64)
- Uses Docker layer caching for efficiency

### 3. Deploy Staging
- Deploys to staging environment on `develop` branch
- Uses Docker Compose for staging deployment
- Runs health checks after deployment

### 4. Deploy Production
- Deploys to Kubernetes cluster on `main` branch
- Uses AWS EKS for production deployment
- Implements rolling updates with health checks
- Automatic rollback on failure

## Required Secrets

Configure these secrets in your GitHub repository:

### AWS Deployment
```
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-west-2
EKS_CLUSTER_NAME=notification-cluster
DOMAIN_NAME=api.yourcompany.com
```

### Staging Environment
```
STAGING_HOST=staging.yourcompany.com
STAGING_USER=deploy
STAGING_SSH_KEY=-----BEGIN PRIVATE KEY-----...
```

## Local Development Deployment

### Quick Start
```bash
# Make deployment script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

### Manual Deployment
```bash
# Start infrastructure
docker-compose up -d redis rabbitmq

# Setup RabbitMQ queues
python setup_rabbitmq.py

# Start all services
docker-compose up -d

# Run health checks
python test_system.py
```

## Production Deployment

### Prerequisites
1. AWS EKS cluster
2. kubectl configured
3. Ingress controller (nginx)
4. Certificate manager (cert-manager)

### Kubernetes Deployment
```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n notification-system
kubectl get services -n notification-system

# View logs
kubectl logs -f deployment/api-gateway-service -n notification-system
```

### Scaling Services
```bash
# Scale API Gateway
kubectl scale deployment api-gateway-service --replicas=5 -n notification-system

# Scale Email Service
kubectl scale deployment email-service --replicas=3 -n notification-system
```

## Monitoring

### Health Checks
All services expose `/api/v1/health/` endpoints:
- API Gateway: http://localhost:8000/api/v1/health/
- User Service: http://localhost:8001/api/v1/health/
- Template Service: http://localhost:8002/api/v1/health/
- Email Service: http://localhost:8003/api/v1/health/
- Push Service: http://localhost:8004/api/v1/health/
- Admin Service: http://localhost:8005/api/v1/health/

### RabbitMQ Monitoring
- Management UI: http://localhost:15672
- Username: guest
- Password: guest

### Kubernetes Monitoring
```bash
# Check pod status
kubectl get pods -n notification-system

# View service logs
kubectl logs -f deployment/email-service -n notification-system

# Check resource usage
kubectl top pods -n notification-system
```

## Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   # Check logs
   docker-compose logs service-name
   
   # Restart specific service
   docker-compose restart service-name
   ```

2. **Database connection issues**
   ```bash
   # Check PostgreSQL status
   docker-compose ps postgres
   
   # Test connection
   docker-compose exec postgres psql -U postgres -d notification_db
   ```

3. **RabbitMQ connection failed**
   ```bash
   # Restart RabbitMQ
   docker-compose restart rabbitmq
   
   # Check queues
   python setup_rabbitmq.py
   ```

4. **Kubernetes deployment issues**
   ```bash
   # Check pod events
   kubectl describe pod pod-name -n notification-system
   
   # Check service endpoints
   kubectl get endpoints -n notification-system
   ```

### Performance Tuning

1. **Database Optimization**
   - Enable connection pooling
   - Add database indexes
   - Configure read replicas

2. **Message Queue Optimization**
   - Adjust prefetch count
   - Configure queue durability
   - Monitor queue lengths

3. **Container Resources**
   - Adjust CPU/memory limits
   - Configure horizontal pod autoscaling
   - Use resource quotas

## Security Considerations

1. **Secrets Management**
   - Use Kubernetes secrets for sensitive data
   - Rotate API keys regularly
   - Enable secret encryption at rest

2. **Network Security**
   - Configure network policies
   - Use TLS for all communications
   - Implement service mesh (optional)

3. **Access Control**
   - Configure RBAC for Kubernetes
   - Use least privilege principle
   - Enable audit logging

## Backup and Recovery

1. **Database Backups**
   ```bash
   # Create backup
   kubectl exec -it postgres-pod -- pg_dump -U postgres notification_db > backup.sql
   
   # Restore backup
   kubectl exec -i postgres-pod -- psql -U postgres notification_db < backup.sql
   ```

2. **Configuration Backups**
   ```bash
   # Export Kubernetes resources
   kubectl get all -n notification-system -o yaml > backup-resources.yaml
   ```

## Performance Targets

- ✅ Handle 1,000+ notifications per minute
- ✅ API Gateway response under 100ms
- ✅ 99.5% delivery success rate
- ✅ Horizontal scaling support
- ✅ Circuit breaker implementation
- ✅ Retry mechanisms with exponential backoff