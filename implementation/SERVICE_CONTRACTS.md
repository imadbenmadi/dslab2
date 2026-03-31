# Service Contracts and NATS Topics Reference

## Overview

All inter-service communication uses strongly-typed contracts defined in `framework/contracts.py` and transported via NATS with mTLS.

---

## Event Contracts

### Vehicle Events

#### VehicleTaskSubmitted

**Topics:**

- `telemetry.vehicle.task-submitted` (default)
- `telemetry.vehicle.task-submitted.fog-service` (targeted)

**Publisher:** Vehicle Service  
**Subscribers:** Fog Service (queue: fog-service), Cloud Service (queue: analytics)

**Schema:**

```python
@dataclass
class VehicleTaskSubmitted:
    vehicle_id: str              # V001, V002, ...
    task_id: str                 # T-00001, T-00002, ...
    classification: str          # "local" | "offload"
    position_x: float            # 0-1000
    position_y: float            # 0-1000
    timestamp_s: float           # Simulation time
    speed_kmh: float             # Vehicle speed
    heading_deg: float           # Direction 0-360
```

**Example:**

```json
{
    "vehicle_id": "V032",
    "task_id": "T-00001",
    "classification": "offload",
    "position_x": 425.3,
    "position_y": 512.7,
    "timestamp_s": 10.5,
    "speed_kmh": 45.0,
    "heading_deg": 180.0
}
```

---

### Fog Events

#### FogDecisionMade

**Topics:**

- `telemetry.fog.decision` (default)
- `telemetry.fog.decision.vehicle-service` (to vehicles)
- `telemetry.fog.decision.cloud-service` (to cloud)

**Publisher:** Fog Service  
**Subscribers:** Vehicle Service, Cloud Service (queue: analytics)

**Schema:**

```python
@dataclass
class FogDecisionMade:
    task_id: str                 # From VehicleTaskSubmitted
    vehicle_id: str              # Which vehicle
    decision: str                # "fog" | "cloud"
    target_fog: Optional[str]    # "A", "B", "C", "D" (None if cloud)
    latency_estimate_ms: float   # Predicted latency
    timestamp_s: float           # Simulation time
```

**Example (Fog Decision):**

```json
{
    "task_id": "T-00001",
    "vehicle_id": "V032",
    "decision": "fog",
    "target_fog": "A",
    "latency_estimate_ms": 8.5,
    "timestamp_s": 10.6
}
```

**Example (Cloud Decision):**

```json
{
    "task_id": "T-00002",
    "vehicle_id": "V033",
    "decision": "cloud",
    "target_fog": null,
    "latency_estimate_ms": 32.0,
    "timestamp_s": 10.7
}
```

---

### Mobility Events

#### HandoffTriggered

**Topics:**

- `telemetry.mobility.handoff` (default)
- `telemetry.mobility.handoff.fog-service` (to fog)

**Publisher:** Fog Service (mobility module)  
**Subscribers:** Cloud Service (queue: analytics)

**Schema:**

```python
@dataclass
class HandoffTriggered:
    vehicle_id: str              # Vehicle initiating handoff
    task_id: str                 # Task being handed off
    source_fog: str              # Current fog node
    target_fog: str              # New fog node
    handoff_type: str            # "proactive" | "reactive"
    new_deadline_ms: float       # Updated deadline in new fog zone
    timestamp_s: float           # Simulation time
```

**Example:**

```json
{
    "vehicle_id": "V032",
    "task_id": "T-00001",
    "source_fog": "A",
    "target_fog": "B",
    "handoff_type": "proactive",
    "new_deadline_ms": 150.0,
    "timestamp_s": 15.2
}
```

---

### Cloud Events

#### CloudForwarded

**Topics:**

- `telemetry.cloud.forwarded` (default)
- `telemetry.cloud.forwarded.cloud-service` (to cloud analytics)

**Publisher:** Fog Service  
**Subscribers:** Cloud Service (queue: analytics)

**Schema:**

```python
@dataclass
class CloudForwarded:
    task_id: str                 # Original task
    vehicle_id: str              # Source vehicle
    source_fog: str              # Forwarding fog node
    forwarding_reason: str       # "boulder" | "overload" | "deadline"
    forwarding_latency_ms: float # Time to reach cloud
    timestamp_s: float           # Simulation time
```

**Example:**

```json
{
    "task_id": "T-00003",
    "vehicle_id": "V010",
    "source_fog": "B",
    "forwarding_reason": "boulder",
    "forwarding_latency_ms": 35.0,
    "timestamp_s": 12.3
}
```

---

#### TaskCompleted

**Topics:**

- `telemetry.task.completed` (default)

**Publisher:** Cloud Service (after execution)  
**Subscribers:** Cloud Service (queue: analytics)

**Schema:**

```python
@dataclass
class TaskCompleted:
    task_id: str                 # Task identifier
    vehicle_id: str              # Origin vehicle
    execution_location: str      # "device" | "fog-{A-D}" | "cloud"
    total_latency_ms: float      # End-to-end latency
    resource_utilization: float  # 0.0-1.0
    success: bool                # Whether task succeeded
    timestamp_s: float           # Completion time
```

**Example:**

```json
{
    "task_id": "T-00001",
    "vehicle_id": "V032",
    "execution_location": "fog-A",
    "total_latency_ms": 18.5,
    "resource_utilization": 0.35,
    "success": true,
    "timestamp_s": 18.1
}
```

---

## Control Plane Events

### PolicySync

**Topics:**

- `control.policy.sync.request` (service requests latest policy)
- `control.policy.sync.response` (policy service responds)

**Schema:**

```python
{
  "policy_version": "1.0",
  "features": {
    "use_agent1": true,
    "use_agent2": true,
    "enable_proactive_handoff": true,
    "sdn_routing_mode": "policy-driven"
  },
  "thresholds": {
    "fog_local_exec_ms": 80,
    "cloud_ec_threshold": 1.0,
    "fog_overload_threshold": 0.75
  }
}
```

---

## NATS Topic Hierarchy

```
telemetry/                          # All observability events
├── vehicle/
│   └── task-submitted
├── fog/
│   ├── decision
│   ├── queue-update
│   └── load-update
├── mobility/
│   └── handoff
├── cloud/
│   ├── forwarded
│   └── completed
└── task/
    ├── executed
    └── completed

control/                            # Control plane
├── policy/
│   ├── sync.request
│   └── sync.response
├── feature-flags/
│   └── update
└── command/
    ├── scale
    └── reconfigure

system/                             # Infrastructure
├── service/
│   ├── heartbeat
│   ├── ready
│   └── shutdown
└── metrics/
    ├── resource-usage
    └── queue-depth
```

---

## Message Wrapper (NatsMessage)

All events are wrapped in this envelope for transport:

```python
@dataclass
class NatsMessage:
    id: str                          # UUID for dedup (e.g., "e7f9c2a1-...")
    topic: str                       # Full NATS topic
    source_service: str              # "vehicle-service", "fog-service", "cloud-service"
    target_service: Optional[str]    # None=broadcast, "fog-service"=unicast
    payload: Dict[str, Any]          # Actual contract event
    timestamp_s: float               # Message creation time
    ack_required: bool               # Whether ack is needed
```

**Example Full Message:**

```json
{
  "id": "e7f9c2a1-4b2f-11ed-8f3d-0242ac110002",
  "topic": "telemetry.vehicle.task-submitted",
  "source_service": "vehicle-service",
  "target_service": "fog-service",
  "payload": {
    "vehicle_id": "V032",
    "task_id": "T-00001",
    ...
  },
  "timestamp_s": 10.5,
  "ack_required": true
}
```

---

## Publishing Patterns

### Broadcast (All Services)

```python
await event_bridge.publish_event("VehicleTaskSubmitted", event_payload, target_service=None)
```

### Unicast (Specific Service)

```python
await event_bridge.publish_event("VehicleTaskSubmitted", event_payload, target_service="fog-service")
```

### Request-Reply (Synchronous)

```python
response = await nats_bus.request(
    "control.policy.sync.request",
    {"service": "vehicle-service"},
    timeout_s=2.0
)
```

---

## Error Handling

### Message Dedup

If a message with the same UUID is published twice, the second is dropped:

```python
if msg_id in bus._seen_ids:
    # Already processed, skip
    continue
```

### Service-Specific Queue Groups

Subscribers use queue groups for load balancing:

```python
await bus.subscribe(
    "telemetry.vehicle.task-submitted",
    handler,
    queue_group="fog-service"  # Only one instance of fog-service receives each message
)
```

### Timeout Handling

If a service doesn't receive expected event within timeout, it logs warning:

```python
try:
    reply = await bus.request(..., timeout_s=5.0)
except asyncio.TimeoutError:
    logger.warning(f"Request timeout after 5s")
```

---

## Versioning Strategy

All contracts include implicit versioning via Python dataclass fields:

```python
# v1.0
@dataclass
class VehicleTaskSubmitted:
    vehicle_id: str
    task_id: str

# v1.1 (backward compatible addition)
@dataclass
class VehicleTaskSubmitted:
    vehicle_id: str
    task_id: str
    priority: int = 0  # New optional field with default
```

For breaking changes, create a new topic:

```
telemetry.vehicle.task-submitted      # v1
telemetry.vehicle.task-submitted.v2   # v2 (if breaking change)
```

---

## Testing Contracts

### Manual Verification

```bash
# Start NATS
nats-server

# Subscribe to all events (in separate terminal)
nats sub telemetry.>

# Publish test event
python -c "
import asyncio
from infrastructure.nats_bus import NatsServiceBus

async def test():
    bus = NatsServiceBus('test', enable_tls=False)
    await bus.connect()
    await bus.publish('telemetry.test', {'sample': 'data'})
    await bus.disconnect()

asyncio.run(test())
"
```

### Automated Testing

See `tests/test_contracts.py` for contract validation:

```bash
python -m pytest tests/test_contracts.py -v
```

---

## Performance Notes

- **Latency per hop:** ~2-5ms (in-process) → ~5-15ms (NATS)
- **Message throughput:** ~10k msg/s per topic (NATS capable of >>100k/s)
- **Dedup overhead:** Negligible (HashMap lookup)
- **mTLS handshake:** ~50-100ms on first connection

---

## Summary

✓ Strongly-typed event contracts (Python dataclasses)  
✓ NATS topics follow service-oriented hierarchy  
✓ All messages wrapped in versioned envelope  
✓ Dedup by UUID to guarantee idempotency  
✓ Queue groups for scalable subscribers  
✓ mTLS with role-based authorization  
✓ Backward-compatible versioning strategy
