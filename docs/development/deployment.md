# Deployment Guide

This guide covers deploying FIML in various environments from development to production.

## Development Deployment

### Quick Start

See [Installation Guide](../getting-started/installation.md) for development setup.

```bash
git clone https://github.com/kiarashplusplus/FIML.git
cd FIML
./quickstart.sh
```

## Production Deployment

### Docker Compose (Small to Medium Scale)

**Best for**: Single server deployments, staging environments

#### 1. Prepare Environment

```bash
# Clone repository
git clone https://github.com/kiarashplusplus/FIML.git
cd FIML

# Create production environment file
cp .env.example .env.production
```

Edit `.env.production` with production settings:

```bash
ENVIRONMENT=production
LOG_LEVEL=WARNING
SERVER_WORKERS=8

# Use strong passwords
POSTGRES_PASSWORD=your_strong_password
REDIS_PASSWORD=your_redis_password

# Add monitoring
SENTRY_DSN=your_sentry_dsn
```

#### 2. Build and Deploy

```bash
# Build production images
docker-compose -f docker-compose.yml build

# Start services
docker-compose -f docker-compose.yml up -d

# Verify deployment
curl http://localhost:8000/health
```

#### 3. Configure Reverse Proxy

Use Nginx or Caddy for SSL termination and load balancing.

**Nginx Example:**

```nginx
server {
    listen 80;
    server_name fiml.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name fiml.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Kubernetes (Large Scale)

**Best for**: Production clusters, high availability, auto-scaling

#### Prerequisites

- Kubernetes cluster (v1.25+)
- kubectl configured
- Helm 3.x

#### 1. Create Namespace

```bash
kubectl create namespace fiml
```

#### 2. Configure Secrets

```bash
kubectl create secret generic fiml-secrets \
  --from-literal=postgres-password=your_password \
  --from-literal=redis-password=your_password \
  --from-literal=alpha-vantage-key=your_key \
  --from-literal=fmp-key=your_key \
  -n fiml
```

#### 3. Deploy with Helm

```bash
# Add FIML Helm repository (if available)
helm repo add fiml https://charts.fiml.ai
helm repo update

# Install
helm install fiml fiml/fiml \
  --namespace fiml \
  --values values-production.yaml
```

Or deploy using kubectl:

```bash
kubectl apply -f k8s/
```

#### 4. Verify Deployment

```bash
kubectl get pods -n fiml
kubectl logs -f deployment/fiml-api -n fiml
```

## Cloud Provider Deployments

### AWS

#### ECS Deployment

Use the provided CloudFormation template:

```bash
aws cloudformation create-stack \
  --stack-name fiml-production \
  --template-body file://cloudformation/ecs-deployment.yaml \
  --parameters file://cloudformation/parameters.json
```

#### EKS Deployment

Deploy to Amazon EKS:

```bash
# Create EKS cluster
eksctl create cluster -f eks-cluster.yaml

# Deploy application
kubectl apply -f k8s/
```

### Google Cloud Platform

#### GKE Deployment

```bash
# Create GKE cluster
gcloud container clusters create fiml-cluster \
  --num-nodes=3 \
  --machine-type=n1-standard-2

# Deploy
kubectl apply -f k8s/
```

### Azure

#### AKS Deployment

```bash
# Create AKS cluster
az aks create \
  --resource-group fiml-rg \
  --name fiml-cluster \
  --node-count 3

# Deploy
kubectl apply -f k8s/
```

## Database Setup

### PostgreSQL

#### Production Configuration

```bash
# In .env.production
POSTGRES_HOST=your-postgres-host
POSTGRES_PORT=5432
POSTGRES_DB=fiml
POSTGRES_USER=fiml
POSTGRES_PASSWORD=strong_password

# Connection pooling
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

#### Managed Database Services

- **AWS RDS**: Use PostgreSQL 14+ with TimescaleDB extension
- **Google Cloud SQL**: PostgreSQL with high availability
- **Azure Database**: PostgreSQL flexible server

### Redis

#### Production Configuration

```bash
# In .env.production
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=strong_password
REDIS_MAX_CONNECTIONS=100
```

#### Managed Redis Services

- **AWS ElastiCache**: Redis cluster mode
- **Google Memorystore**: Redis with HA
- **Azure Cache**: Redis premium tier

## Monitoring Setup

### Prometheus

Already configured in docker-compose.yml:

```yaml
prometheus:
  image: prom/prometheus
  ports:
    - "9091:9090"
  volumes:
    - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
```

### Grafana

Access dashboards at http://localhost:3000:

Default credentials: admin/admin

Import provided dashboards:
- FIML API Metrics
- Cache Performance
- Provider Health

### Sentry

Add to `.env.production`:

```bash
SENTRY_DSN=your_sentry_dsn
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

## Scaling Considerations

### Horizontal Scaling

Scale API instances:

```bash
# Docker Compose
docker-compose up -d --scale api=4

# Kubernetes
kubectl scale deployment fiml-api --replicas=4 -n fiml
```

### Vertical Scaling

Adjust resource limits:

```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
```

### Cache Scaling

- **Redis**: Use Redis Cluster for large datasets
- **PostgreSQL**: Enable read replicas for L2 cache

## Backup & Recovery

### Database Backups

```bash
# PostgreSQL backup
docker-compose exec postgres pg_dump -U fiml fiml > backup.sql

# Restore
docker-compose exec -T postgres psql -U fiml fiml < backup.sql
```

### Automated Backups

Configure in cloud provider:
- AWS RDS: Automated snapshots
- Google Cloud SQL: Automated backups
- Azure: Automated backup policy

## Security Checklist

- [ ] Use strong passwords for all services
- [ ] Enable SSL/TLS for all connections
- [ ] Configure firewall rules
- [ ] Enable API authentication
- [ ] Set up rate limiting
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Secrets management (Vault, AWS Secrets Manager)
- [ ] Network isolation
- [ ] Enable CORS properly

## Health Checks

### API Health

```bash
curl http://localhost:8000/health
```

### Database Health

```bash
curl http://localhost:8000/health/db
```

### Cache Health

```bash
curl http://localhost:8000/health/cache
```

## Troubleshooting

### Container Logs

```bash
# Docker Compose
docker-compose logs -f api

# Kubernetes
kubectl logs -f deployment/fiml-api -n fiml
```

### Database Connection Issues

Check connection string and credentials:

```bash
docker-compose exec api python -c "from fiml.db import test_connection; test_connection()"
```

### Memory Issues

Monitor memory usage:

```bash
docker stats
```

Adjust limits if needed in docker-compose.yml.

## Next Steps

- Set up [Monitoring](../operations/monitoring.md)
- Configure [CI/CD Pipeline](https://github.com/kiarashplusplus/FIML/blob/main/.github/workflows/ci.yml)
- Review [Security Best Practices](../architecture/overview.md#security)
