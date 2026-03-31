# Deployment Guide for Distributed Services

This guide covers deploying the Smart City system in various environments: local development, Docker, Kubernetes, and cloud platforms.

## Deployment Targets

1. **Local Development** (single machine, all services)
2. **Docker Compose** (containerized, local network)
3. **Kubernetes** (production-grade, multiple nodes)
4. **Cloud Platforms** (AWS ECS, Azure Container Instances, Google Cloud Run)

---

## 1. Local Development Deployment

### Prerequisites

```bash
# Python 3.9+
python --version

# Node.js 16+
node --version

# Docker (optional, for NATS)
docker --version
```

### Installation

```bash
# Clone/navigate to implementation directory
cd implementation

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..

# Verify setup
python check_setup.py
```

### Running Services

**Terminal 1: NATS Broker**

```bash
docker run -d --name nats-dev -p 4222:4222 nats:latest
```

**Terminal 2: All three services**

```bash
python -m services.orchestrator
```

**Terminal 3: Frontend**

```bash
cd frontend && npm start
```

**Access:**

- Dashboard: http://localhost:3000
- API: http://127.0.0.1:5000
- WebSocket: ws://127.0.0.1:8765

---

## 2. Docker Compose Deployment

### Setup

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
    # NATS message broker
    nats:
        image: nats:latest
        container_name: nats-broker
        ports:
            - "4222:4222"
            - "6222:6222"
            - "8222:8222"
        volumes:
            - ./nats.conf:/etc/nats/nats.conf
        command: ["-c", "/etc/nats/nats.conf"]
        networks:
            - smartcity

    # Vehicle Service
    vehicle-service:
        build:
            context: .
            dockerfile: Dockerfile.service
            args:
                SERVICE_NAME: vehicle-service
                ENTRYPOINT: "python -m services.vehicle_service"
        container_name: vehicle-service
        depends_on:
            - nats
        environment:
            NATS_URL: nats://nats:4222
            CERT_DIR: /app/certs
            LOG_LEVEL: INFO
        volumes:
            - ./certs:/app/certs
            - ./results/logs:/app/results/logs
        networks:
            - smartcity
        restart: unless-stopped

    # Fog Service
    fog-service:
        build:
            context: .
            dockerfile: Dockerfile.service
            args:
                SERVICE_NAME: fog-service
                ENTRYPOINT: "python -m services.fog_service"
        container_name: fog-service
        depends_on:
            - nats
        environment:
            NATS_URL: nats://nats:4222
            CERT_DIR: /app/certs
            LOG_LEVEL: INFO
        volumes:
            - ./certs:/app/certs
            - ./results/logs:/app/results/logs
        networks:
            - smartcity
        restart: unless-stopped

    # Cloud Service
    cloud-service:
        build:
            context: .
            dockerfile: Dockerfile.service
            args:
                SERVICE_NAME: cloud-service
                ENTRYPOINT: "python -m services.cloud_service"
        container_name: cloud-service
        depends_on:
            - nats
        ports:
            - "5000:5000"
            - "8765:8765"
        environment:
            NATS_URL: nats://nats:4222
            CERT_DIR: /app/certs
            LOG_LEVEL: INFO
        volumes:
            - ./certs:/app/certs
            - ./results/logs:/app/results/logs
        networks:
            - smartcity
        restart: unless-stopped

    # Frontend
    frontend:
        build:
            context: ./frontend
            dockerfile: Dockerfile
        container_name: dashboard
        ports:
            - "3000:3000"
        depends_on:
            - cloud-service
        environment:
            REACT_APP_API_URL: http://localhost:5000
            REACT_APP_WS_URL: ws://localhost:8765
        networks:
            - smartcity
        restart: unless-stopped

networks:
    smartcity:
        driver: bridge
```

### Dockerfiles

**Dockerfile.service:**

```dockerfile
FROM python:3.11-slim

ARG SERVICE_NAME
ARG ENTRYPOINT

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create directories
RUN mkdir -p certs results/logs

# Set environment
ENV SERVICE_NAME=$SERVICE_NAME
ENV PYTHONUNBUFFERED=1

# Run service
CMD $ENTRYPOINT
```

**frontend/Dockerfile:**

```dockerfile
FROM node:18-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

### Run Compose

```bash
# Generate certificates if needed
python check_setup.py

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f cloud-service

# Stop services
docker-compose down
```

---

## 3. Kubernetes Deployment

### Prerequisites

```bash
# Install kubectl
kubectl version --client

# Kubernetes cluster (minikube, EKS, GKE, AKS, etc.)
kubectl cluster-info
```

### Container Images

Build and push images to registry:

```bash
# Push to DockerHub (or any registry)
docker build -t myregistry/vehicle-service:1.0 -f Dockerfile.service .
docker build -t myregistry/fog-service:1.0 -f Dockerfile.service .
docker build -t myregistry/cloud-service:1.0 -f Dockerfile.service .

docker push myregistry/vehicle-service:1.0
docker push myregistry/fog-service:1.0
docker push myregistry/cloud-service:1.0
```

### Kubernetes Manifests

**k8s/namespace.yaml:**

```yaml
apiVersion: v1
kind: Namespace
metadata:
    name: smartcity
```

**k8s/nats-deployment.yaml:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
    name: nats-broker
    namespace: smartcity
spec:
    replicas: 1
    selector:
        matchLabels:
            app: nats
    template:
        metadata:
            labels:
                app: nats
        spec:
            containers:
                - name: nats
                  image: nats:latest
                  ports:
                      - containerPort: 4222
                        name: client
                      - containerPort: 6222
                        name: route
                      - containerPort: 8222
                        name: monitor
---
apiVersion: v1
kind: Service
metadata:
    name: nats-service
    namespace: smartcity
spec:
    selector:
        app: nats
    ports:
        - name: client
          port: 4222
          targetPort: 4222
        - name: route
          port: 6222
          targetPort: 6222
    clusterIP: None # Headless service
```

**k8s/vehicle-service.yaml:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
    name: vehicle-service
    namespace: smartcity
spec:
    replicas: 1
    selector:
        matchLabels:
            app: vehicle-service
    template:
        metadata:
            labels:
                app: vehicle-service
        spec:
            containers:
                - name: vehicle-service
                  image: myregistry/vehicle-service:1.0
                  imagePullPolicy: Always
                  env:
                      - name: NATS_URL
                        value: "nats://nats-service:4222"
                      - name: LOG_LEVEL
                        value: "INFO"
                  resources:
                      requests:
                          cpu: "100m"
                          memory: "512Mi"
                      limits:
                          cpu: "500m"
                          memory: "1Gi"
                  volumeMounts:
                      - name: certs
                        mountPath: /app/certs
                        readOnly: true
            volumes:
                - name: certs
                  secret:
                      secretName: service-certs
---
apiVersion: v1
kind: ConfigMap
metadata:
    name: vehicle-config
    namespace: smartcity
data:
    nats_url: "nats://nats-service:4222"
    log_level: "INFO"
```

### Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets for certs
kubectl create secret generic service-certs \
  --from-file=certs/ \
  -n smartcity

# Deploy NATS
kubectl apply -f k8s/nats-deployment.yaml

# Deploy services
kubectl apply -f k8s/vehicle-service.yaml
kubectl apply -f k8s/fog-service.yaml
kubectl apply -f k8s/cloud-service.yaml

# Check deployment status
kubectl get pods -n smartcity
kubectl describe deployment vehicle-service -n smartcity

# View logs
kubectl logs -f deployment/vehicle-service -n smartcity

# Port forwarding to access services
kubectl port-forward -n smartcity svc/cloud-service 5000:5000
kubectl port-forward -n smartcity svc/cloud-service 8765:8765

# Delete deployment
kubectl delete namespace smartcity
```

### Scaling

```bash
# Scale vehicle service to 3 replicas
kubectl scale deployment/vehicle-service --replicas=3 -n smartcity

# Auto-scaling (requires metrics-server)
kubectl autoscale deployment vehicle-service \
  --min=1 --max=5 \
  --cpu-percent=80 \
  -n smartcity
```

---

## 4. Cloud Platforms

### AWS ECS

```bash
# Create ECR repositories
aws ecr create-repository --repository-name vehicle-service
aws ecr create-repository --repository-name fog-service
aws ecr create-repository --repository-name cloud-service

# Push images
aws ecr get-login-password | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com
docker tag vehicle-service:1.0 <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/vehicle-service:1.0
docker push <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/vehicle-service:1.0

# Create ECS cluster
aws ecs create-cluster --cluster-name smartcity

# Register task definitions and create services
# (Use ECS console or AWS CLI)
```

### Google Cloud Run

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/<PROJECT>/vehicle-service

# Deploy to Cloud Run
gcloud run deploy vehicle-service \
  --image gcr.io/<PROJECT>/vehicle-service \
  --platform managed \
  --region us-central1 \
  --memory 512Mi \
  --env-vars-file .env

# Check status
gcloud run describe vehicle-service --platform managed --region us-central1
```

### Azure Container Instances

```bash
# Create registry
az acr create --resource-group <RG> --name <REGISTRY> --sku Basic

# Push images
az acr build --registry <REGISTRY> --image vehicle-service:1.0 .

# Deploy container group
az container create \
  --resource-group <RG> \
  --name smartcity-group \
  --image <REGISTRY>.azurecr.io/vehicle-service:1.0 \
  --cpu 1 --memory 1
```

---

## Environment Variables

All services support these environment variables:

```bash
NATS_URL=nats://localhost:4222          # NATS broker URL
CERT_DIR=./certs                        # Certificate directory
CERT_TLS_ENABLED=true                   # Enable/disable TLS
LOG_LEVEL=INFO                          # Logging: DEBUG, INFO, WARNING, ERROR
SIMULATION_DURATION_S=600               # Total simulation time
VEHICLE_service_count=50                # Number of vehicles
FOG_NODE_COUNT=4                        # Number of fog nodes
```

---

## Monitoring and Observability

### Prometheus Metrics

Add Prometheus exporter to each service:

```python
from prometheus_client import Counter, Histogram, start_http_server

# In each service
tasks_submitted = Counter('tasks_submitted_total', 'Total tasks')
task_latency = Histogram('task_latency_seconds', 'Task latency')
start_http_server(8000)  # Metrics on :8000/metrics
```

### Logging

All services log to:

- stdout (captured by container logs)
- `results/logs/system.log`
- `results/logs/events.jsonl`

### Health Checks

Kubernetes health checks:

```yaml
livenessProbe:
    httpGet:
        path: /api/health
        port: 5000
    initialDelaySeconds: 30
    periodSeconds: 10

readinessProbe:
    httpGet:
        path: /api/cloud/status
        port: 5000
    initialDelaySeconds: 10
    periodSeconds: 5
```

---

## Troubleshooting

### Certificate Issues

```bash
# Verify certificates
openssl x509 -in certs/vehicle-service.crt -text -noout

# Regenerate if corrupted
rm -rf certs/
python check_setup.py  # Regenerates
```

### NATS Connection Issues

```bash
# Test NATS connectivity
nats pub test "hello" --server nats://localhost:4222

# Monitor NATS
nats --server=nats://localhost:4222 sub telemetry.>
```

### Container Debugging

```bash
# Exec into running container
docker exec -it vehicle-service bash

# View Docker logs
docker logs -f vehicle-service

# Inspect network
docker network inspect smartcity
```

### Kubernetes Debugging

```bash
# Get pod events
kubectl describe pod vehicle-service-xxxxx -n smartcity

# Execute command in pod
kubectl exec -it vehicle-service-xxxxx -n smartcity -- bash

# View resource usage
kubectl top nodes
kubectl top pods -n smartcity
```

---

## Performance Recommendations

| Component    | Recommendation                                     |
| ------------ | -------------------------------------------------- |
| CPU requests | 100m per service (development), 500m (production)  |
| Memory       | 512Mi per service (minimum)                        |
| NATS         | 1Gi memory, persistent volume for durability       |
| Storage      | 10Gi for results/logs                              |
| Network      | Dedicated network (no shared with other workloads) |

---

## Security Checklist

- ✓ mTLS enabled between all services
- ✓ Certificates rotated regularly (90-180 days)
- ✓ NATS server runs with TLS
- ✓ Secrets stored in secrets manager (not in code)
- ✓ RBAC configured for Kubernetes
- ✓ Network policies restrict traffic
- ✓ Logs encrypted and access-controlled
- ✓ Regular backups of state/results

---

## Summary

| Deployment     | Complexity | Scalability           | Cost             |
| -------------- | ---------- | --------------------- | ---------------- |
| Local Dev      | ⭐         | Single machine        | Free             |
| Docker Compose | ⭐⭐       | Single machine        | Free             |
| Kubernetes     | ⭐⭐⭐⭐   | Multi-node cluster    | $$               |
| Cloud Run      | ⭐⭐       | Serverless auto-scale | $$ (usage-based) |

**Recommended for production:** Kubernetes with auto-scaling and Prometheus monitoring.
