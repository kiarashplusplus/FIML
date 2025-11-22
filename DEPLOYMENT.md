# FIML Deployment Guide

## Quick Start (Development)

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Git

### 1. Clone and Setup

```bash
git clone https://github.com/your-org/fiml.git
cd fiml
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start Services

```bash
# Build and start all services
make build
make up

# Verify health
curl http://localhost:8000/health
```

### 3. Test the API

```bash
# Using curl
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "search-by-symbol",
    "arguments": {
      "symbol": "TSLA",
      "market": "US",
      "depth": "standard"
    }
  }'

# Using Python
python examples/basic_usage.py
```

## Production Deployment

### Option 1: Docker Compose (Recommended for Small/Medium Scale)

1. **Update environment variables**
```bash
cp .env.example .env.production
# Edit .env.production with production settings
```

2. **Build production image**
```bash
docker-compose -f docker-compose.yml build
```

3. **Deploy**
```bash
docker-compose -f docker-compose.yml up -d
```

4. **Configure reverse proxy (Nginx)**
```nginx
server {
    listen 80;
    server_name fiml.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Option 2: Kubernetes (Recommended for Large Scale)

1. **Build and push image**
```bash
docker build -t your-registry/fiml:latest .
docker push your-registry/fiml:latest
```

2. **Create namespace**
```bash
kubectl create namespace fiml
```

3. **Deploy manifests**
```bash
kubectl apply -f k8s/
```

4. **Verify deployment**
```bash
kubectl get pods -n fiml
kubectl get svc -n fiml
```

### Option 3: Cloud Platforms

#### AWS (ECS/EKS)
```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin xxx.dkr.ecr.us-east-1.amazonaws.com
docker build -t fiml:latest .
docker tag fiml:latest xxx.dkr.ecr.us-east-1.amazonaws.com/fiml:latest
docker push xxx.dkr.ecr.us-east-1.amazonaws.com/fiml:latest
```

#### Google Cloud (GKE)
```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/fiml:latest
gcloud run deploy fiml --image gcr.io/PROJECT_ID/fiml:latest --platform managed
```

## Environment Configuration

### Required Environment Variables

```bash
# Server
FIML_ENV=production
FIML_HOST=0.0.0.0
FIML_PORT=8000

# Database
POSTGRES_HOST=your-postgres-host
POSTGRES_DB=fiml
POSTGRES_USER=fiml
POSTGRES_PASSWORD=<secure-password>

# Cache
REDIS_HOST=your-redis-host
REDIS_PASSWORD=<secure-password>

# API Keys
ALPHA_VANTAGE_API_KEY=your-key
FMP_API_KEY=your-key
```

### Security Considerations

1. **Change default passwords**
2. **Use secrets management** (AWS Secrets Manager, HashiCorp Vault, etc.)
3. **Enable HTTPS** (use Let's Encrypt or cloud provider certificates)
4. **Configure firewall rules**
5. **Enable rate limiting**
6. **Set up monitoring and alerts**

## Scaling

### Horizontal Scaling

Scale the MCP server:
```bash
docker-compose up -d --scale fiml-server=3
```

Or in Kubernetes:
```bash
kubectl scale deployment fiml-server --replicas=5 -n fiml
```

### Vertical Scaling

Update resource limits in `docker-compose.yml`:
```yaml
services:
  fiml-server:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## Monitoring

### Access Dashboards

- **Grafana**: http://your-domain:3000 (admin/admin)
- **Prometheus**: http://your-domain:9090
- **Ray Dashboard**: http://your-domain:8265

### Key Metrics to Monitor

- Request rate and latency
- Error rate
- Provider health scores
- Cache hit rate
- Database connections
- Memory and CPU usage

### Alerting

Configure alerts in `config/prometheus/alerts.yml`:
```yaml
groups:
  - name: fiml
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status="500"}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
```

## Backup and Recovery

### Database Backup

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U fiml fiml > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T postgres psql -U fiml fiml < backup_20250101.sql
```

### Redis Backup

```bash
# Redis automatically persists to disk (AOF enabled)
# Copy dump.rdb and appendonly.aof files
```

## Troubleshooting

### Check logs
```bash
make logs
# or
docker-compose logs -f fiml-server
```

### Check service health
```bash
curl http://localhost:8000/health
```

### Database connection issues
```bash
# Test PostgreSQL connection
docker-compose exec postgres psql -U fiml -d fiml -c "SELECT 1;"
```

### Redis connection issues
```bash
# Test Redis connection
docker-compose exec redis redis-cli ping
```

## Performance Tuning

### Database Optimization

```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM price_cache WHERE asset_id = 1;

-- Vacuum database
VACUUM ANALYZE;
```

### Cache Tuning

Adjust TTL values in `.env`:
```bash
CACHE_TTL_PRICE=10        # 10 seconds for price data
CACHE_TTL_FUNDAMENTALS=3600  # 1 hour for fundamentals
```

### Ray Worker Configuration

Scale worker nodes:
```yaml
ray-worker:
  deploy:
    replicas: 4  # Increase for more parallel processing
```

## Maintenance

### Update Dependencies

```bash
pip install --upgrade -r requirements.txt
```

### Rotate API Keys

1. Update `.env` with new keys
2. Restart services:
```bash
docker-compose restart fiml-server
```

### Clean Up Old Data

```bash
# Clean old task results (older than 7 days)
docker-compose exec postgres psql -U fiml -d fiml -c "DELETE FROM tasks WHERE created_at < NOW() - INTERVAL '7 days' AND status = 'completed';"
```

## Support

- **Documentation**: [docs.fiml.ai](https://docs.fiml.ai)
- **GitHub Issues**: [github.com/your-org/fiml/issues](https://github.com/your-org/fiml/issues)
- **Discord**: [Join community](https://discord.gg/fiml)
