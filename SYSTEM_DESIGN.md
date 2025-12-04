# Distributed Notification System - System Design

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │    │   Admin Panel   │    │   Monitoring    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway Service                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │ Auth/Valid  │ │   Routing   │ │   Tracking  │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
└─────────┬───────────────────────────────────────┬─────────────┘
          │                                       │
          ▼                                       ▼
┌─────────────────┐                    ┌─────────────────┐
│  User Service   │                    │ Template Service│
│ ┌─────────────┐ │                    │ ┌─────────────┐ │
│ │User Data/   │ │                    │ │Templates/   │ │
│ │Preferences  │ │                    │ │Variables    │ │
│ └─────────────┘ │                    │ └─────────────┘ │
└─────────────────┘                    └─────────────────┘
          │                                       │
          ▼                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RabbitMQ Message Queue                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │email.queue  │ │ push.queue  │ │failed.queue │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
└─────────┬───────────────────────────────────────┬─────────────┘
          │                                       │
          ▼                                       ▼
┌─────────────────┐                    ┌─────────────────┐
│  Email Service  │                    │  Push Service   │
│ ┌─────────────┐ │                    │ ┌─────────────┐ │
│ │SMTP/SendGrid│ │                    │ │FCM/OneSignal│ │
│ │Circuit Break│ │                    │ │Circuit Break│ │
│ └─────────────┘ │                    │ └─────────────┘ │
└─────────────────┘                    └─────────────────┘
```

## Database Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Service  │    │Template Service │    │ Email Service   │
│   PostgreSQL    │    │   PostgreSQL    │    │   PostgreSQL    │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   Users     │ │    │ │ Templates   │ │    │ │EmailNotif.  │ │
│ │ Preferences │ │    │ │ Versions    │ │    │ │DeliveryLogs │ │
│ │   Devices   │ │    │ │ Languages   │ │    │ └─────────────┘ │
│ └─────────────┘ │    │ └─────────────┘ │    └─────────────────┘
└─────────────────┘    └─────────────────┘
          │                      │
          ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Redis Cache                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │User Prefs   │ │Rate Limits  │ │Session Data │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## Message Flow & Retry Logic

```
1. Request → API Gateway
2. Validate User → User Service
3. Queue Message → RabbitMQ
4. Process → Email/Push Service
5. Get Template → Template Service
6. Send Notification → SMTP/FCM
7. Update Status → User Service

Retry Flow:
┌─────────────┐    Retry 1-5x     ┌─────────────┐
│   Failed    │ ──────────────→   │   Retry     │
│ Notification│                   │   Queue     │
└─────────────┘                   └─────────────┘
       │                                 │
       │ Max Retries Exceeded            │ Success
       ▼                                 ▼
┌─────────────┐                   ┌─────────────┐
│Dead Letter  │                   │  Delivered  │
│   Queue     │                   │   Status    │
└─────────────┘                   └─────────────┘
```

## Circuit Breaker Pattern

```
┌─────────────┐    Success     ┌─────────────┐
│   CLOSED    │ ──────────→    │   CLOSED    │
│  (Normal)   │                │  (Normal)   │
└─────────────┘                └─────────────┘
       │                              ▲
       │ Failure Threshold             │
       ▼                              │ Success
┌─────────────┐    Timeout     ┌─────────────┐
│    OPEN     │ ──────────→    │ HALF_OPEN   │
│ (Blocked)   │                │ (Testing)   │
└─────────────┘                └─────────────┘
```

## Scaling Strategy

### Horizontal Scaling
- **API Gateway**: Load balancer + multiple instances
- **Services**: Container orchestration (Docker + Kubernetes)
- **Database**: Read replicas for User/Template services
- **Queue**: RabbitMQ clustering
- **Cache**: Redis clustering

### Performance Targets
- **Throughput**: 1,000+ notifications/minute
- **Latency**: API Gateway < 100ms
- **Reliability**: 99.5% delivery success
- **Availability**: 99.9% uptime

## Monitoring & Observability

### Metrics to Track
- Message queue length and processing rate
- Service response times and error rates
- Database connection pool usage
- Circuit breaker state changes
- Notification delivery success rates

### Logging Strategy
- Correlation IDs for request tracing
- Structured logging (JSON format)
- Centralized log aggregation
- Alert thresholds for critical errors

## Security & API Keys

### Inter-Service Authentication
```
Admin Service → Generates API Keys
     │
     ├── API_GATEWAY_KEY → User Service access
     ├── EMAIL_SERVICE_KEY → Template Service access
     ├── PUSH_SERVICE_KEY → Template Service access
     └── Service-specific keys for internal communication
```

### Access Control Matrix
| Service | Can Access | Purpose |
|---------|------------|---------|
| API Gateway | User Service | User validation |
| Email Service | Template Service, User Service | Templates, status updates |
| Push Service | Template Service, User Service | Templates, status updates |

## Deployment Architecture

### CI/CD Pipeline
1. **Test**: Unit tests, integration tests
2. **Build**: Docker images for each service
3. **Deploy**: Rolling deployment with health checks
4. **Monitor**: Automated rollback on failure

### Infrastructure
- **Containers**: Docker + Docker Compose (dev) / Kubernetes (prod)
- **Load Balancer**: Nginx or cloud load balancer
- **Database**: PostgreSQL with connection pooling
- **Cache**: Redis with persistence
- **Queue**: RabbitMQ with management UI
- **Monitoring**: Prometheus + Grafana + AlertManager