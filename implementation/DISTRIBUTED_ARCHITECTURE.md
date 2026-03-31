# Distributed Microservices Architecture

This document explains the transition from monolithic to distributed architecture with three independent services communicating via NATS with mTLS.

## Architecture Overview

```
┌────────────────────┐         ┌──────────────────┐         ┌───────────────────┐
│ Vehicle Service    │         │  Fog Service     │         │ Cloud Service     │
│                    │         │                  │         │                   │
│ • Vehicles (N)     │◄────────┤ • Fog Nodes (4)  │◄────────┤ • Flask API       │
│ • Agent1 (place)   │  NATS   │ • Agent2 (route) │  NATS   │ • WebSocket       │
│ • TOF (lite)       │  mTLS   │ • SDN Controller │  mTLS   │ • Analytics       │
└────────────────────┘         └──────────────────┘         │ • Control Plane   │
         ▲                              ▲                    └───────────────────┘
         │                              │
         └──────────────┬───────────────┘
              NATS with mTLS
           (Contracts/Events)
```

## The Three Services

### 1. **Vehicle Service** (`services/vehicle_service.py`)

**Responsibility:** Vehicle-side intelligence and task generation

**Components:**

- Vehicle simulation (N=50 vehicles)
- Agent1 (DQN task placement classifier)
- TOF-lite broker (vehicle-side threshold)
- Task generation at 10 Hz

**NATS Subscriptions:**

- `telemetry.fog.decision` – Receives fog routing decisions

**NATS Publications:**

- `telemetry.vehicle.task-submitted` → fog-service

**Run:**

```bash
python -m services.vehicle_service
```

---

### 2. **Fog Service** (`services/fog_service.py`)

**Responsibility:** Fog node orchestration and first-level routing

**Components:**

- 4 fog nodes with coverage radius
- Agent2 (DQN routing classifier)
- SDN controller for path selection
- Authoritative TOF broker (threshold + load-aware)

**NATS Subscriptions:**

- `telemetry.vehicle.task-submitted` – Tasks from vehicles

**NATS Publications:**

- `telemetry.fog.decision` → vehicle-service
- `telemetry.fog.decision` → cloud-service (for cloud tasks)
- `telemetry.cloud.forwarded` (if boulder → cloud)

**Run:**

```bash
python -m services.fog_service
```

---

### 3. **Cloud Service** (`services/cloud_service.py`)

**Responsibility:** Analytics, API, control plane, and cloud compute

**Components:**

- Flask REST API (port 5000)
- WebSocket server (port 8765)
- Event analytics engine
- Policy and control plane
- Task completion tracking

**NATS Subscriptions:**

- All telemetry topics (queue group: analytics)
- `telemetry.*` – Aggregates all events for metrics

**NATS Publications:**

- Control commands (policies, feature flags)

**API Endpoints:**

- `GET /api/cloud/analytics` – Task metrics
- `GET /api/cloud/status` – Service health
- `GET /api/health` – General health

**Run:**

```bash
python -m services.cloud_service
```

---

## Communication Contract

All inter-service communication uses **contract events** defined in `framework/contracts.py`:

```python
@dataclass
class VehicleTaskSubmitted:
    vehicle_id: str
    task_id: str
    classification: str  # "local" | "offload"
    position_x: float
    position_y: float
    timestamp_s: float

@dataclass
class FogDecisionMade:
    task_id: str
    vehicle_id: str
    decision: str  # "fog" | "cloud"
    target_fog: Optional[str]
    timestamp_s: float

@dataclass
class CloudForwarded:
    task_id: str
    latency_ms: float
    resource_utilization: float
    timestamp_s: float
```

### NATS Message Format

All events are wrapped in a versioned envelope:

```python
@dataclass
class NatsMessage:
    id: str                      # UUID for dedup
    topic: str                   # telemetry.vehicle.task-submitted
    source_service: str          # vehicle-service
    target_service: Optional[str] # None = broadcast, else specific service
    payload: Dict[str, Any]      # Actual event data
    timestamp_s: float
    ack_required: bool
```

---

## mTLS and Role-Based Authorization

### Certificate Hierarchy

```
CA (certs/ca.crt, certs/ca.key)
├── vehicle-service.crt (role: vehicle)
├── fog-service.crt (role: fog)
└── cloud-service.crt (role: cloud)
```

### Certificate Generation

On first orchestrator startup, all certificates are auto-generated:

```bash
python -m services.orchestrator
```

This creates:

- `certs/ca.crt` – Root CA (self-signed)
- `certs/vehicle-service.{crt,key}` – Vehicle service mTLS pair
- `certs/fog-service.{crt,key}` – Fog service mTLS pair
- `certs/cloud-service.{crt,key}` – Cloud service mTLS pair
- `certs/certs.json` – Index of all certificates

### Mutual TLS

Each service connects to NATS with:

```python
conn = await nats.connect(
    nats_url,
    tls_cert_file=mtls_config["cert"],
    tls_key_file=mtls_config["key"],
    tls_ca_file=mtls_config["ca"],
)
```

### Role-Based Authorization

Services validate peer roles via certificate CN and OU fields:

```python
identity = IdentityRegistry()
identity.register(DeviceIdentity(
    device_id="fog-service",
    role="fog",
    cert_fingerprint="..."
))

if identity.is_allowed(peer_id, required_role="fog"):
    # Process request
```

---

## NATS Broker Setup

### Local Development (Docker)

```bash
docker run -d --name nats-server -p 4222:4222 nats:latest
```

### With mTLS (Production)

Create NATS config:

```conf
listen: 127.0.0.1:4222

tls: {
  cert_file: "path/to/server.crt"
  key_file: "path/to/server.key"
  ca_file: "path/to/ca.crt"
  verify: true
}
```

Then run:

```bash
nats-server -c nats.conf
```

---

## Service Startup Sequence

### Using Orchestrator (Recommended)

```bash
# Install dependencies
pip install -r requirements.txt

# Start NATS broker (in separate terminal)
nats-server

# Run orchestrator (starts all three services)
python -m services.orchestrator
```

### Manual Startup (Debugging)

Terminal 1:

```bash
nats-server
```

Terminal 2:

```bash
python -m services.vehicle_service
```

Terminal 3:

```bash
python -m services.fog_service
```

Terminal 4:

```bash
python -m services.cloud_service
```

---

## Data Flow Example

1. **Vehicle Task Submission:**
    - Vehicle V001 generates task T-00001
    - Vehicle-service publishes `VehicleTaskSubmitted` event to NATS
    - Message ID: `e7f9c2a1-...` (dedup tracking)

2. **Fog Decision:**
    - Fog-service subscribes to `telemetry.vehicle.task-submitted`
    - Finds nearest fog node (Fog-A, 150m away)
    - Checks load (0.35) vs threshold
    - Publishes `FogDecisionMade(decision="fog", target_fog="A")`

3. **Cloud Analytics:**
    - Cloud-service subscribes to all telemetry topics
    - Updates metrics: `tasksOffloadedToFog++`
    - Broadcasts update to WebSocket clients
    - Stores event in task log

---

## Messaging Guarantees

- **At-least-once delivery:** Dedup by message ID (`NatsMessage.id`)
- **No ordering guarantee:** NATS preserves publish order per subject, but services consume concurrently
- **Fire-and-forget:** Most events are asynchronous
- **Request-reply:** Available for synchronous operations (not currently used)

---

## Debugging and Observability

### Check NATS Connection Health

```bash
# List all subscriptions
nats sub --all-subscriptions

# Monitor published messages
nats sub telemetry.>
```

### Service Status Endpoints

```bash
# Vehicle service (implicit, no HTTP)

# Fog service (implicit, no HTTP)

# Cloud service
curl http://127.0.0.1:5000/api/cloud/status
curl http://127.0.0.1:5000/api/cloud/analytics
```

### Certificate Verification

```bash
# Inspect service certificate
openssl x509 -in certs/vehicle-service.crt -text -noout

# Check CA validity
openssl x509 -in certs/ca.crt -text -noout
```

---

## Migration from Monolithic App

### Old Architecture

- Single `app.py` process
- In-memory `AtLeastOnceBus`
- All logic in one Python process
- WebSocket and Flask in same process

### New Architecture

- Three separate Python processes
- NATS message broker (external dependency)
- Contracts validate all messages
- Services are independently deployable
- Better scalability and fault isolation

### Backward Compatibility

The old monolithic `app.py` remains available for reference but is deprecated. To use:

```bash
python app.py proposed
```

This will display a deprecation notice recommending the distributed services.

---

## Performance Characteristics

| Metric            | Monolithic                | Distributed                         |
| ----------------- | ------------------------- | ----------------------------------- |
| Startup time      | ~2-3s                     | 5-8s (NATS + certs)                 |
| Task latency      | <5ms (in-process)         | 5-15ms (NATS + network)             |
| Scalability       | Limited by single process | Unlimited (add services)            |
| Failure isolation | All-or-nothing            | Graceful degradation                |
| Debug complexity  | Single process            | Multi-process (easier in some ways) |

---

## Future Enhancements

1. **Kubernetes Deployment:** Deploy services as separate pods with service discovery
2. **Event Sourcing:** Store all NATS events for replay/audit
3. **Circuit Breaker:** Auto-recover from temporary NATS outages
4. **Metrics Export:** Prometheus metrics from each service
5. **Distributed Tracing:** OpenTelemetry correlation across services
6. **Dynamic Policy Sync:** Update routing policies without restart

---

## Summary

**Key Changes:**

✓ Split monolithic app into three focused services  
✓ Replaced in-memory bus with NATS for inter-service communication  
✓ Added mTLS for service-to-service authentication  
✓ Role-based authorization via certificate attributes  
✓ Contracts enforce message schema across services  
✓ Improved scalability and fault isolation

**To Run:**

```bash
pip install -r requirements.txt
nats-server &  # Start NATS in background
python -m services.orchestrator  # Start all three services
```
