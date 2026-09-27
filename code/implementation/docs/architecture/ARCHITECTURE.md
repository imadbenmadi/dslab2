# System Architecture

## Overview

Smart City Vehicular Task Offloading is a distributed simulation with real-time dashboard.

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Dashboard                          │
│                  (http://localhost:3000)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ WebSocket + REST
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Flask API Server (5000)                      │
│  • /api/status          → System state                         │
│  • /api/metrics/history → Historical data                      │
│  • /api/map/state       → Vehicle positions & connections     │
│  • /api/evaluation/*    → Baseline comparison                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                 Simulation Engine (SimPy)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  50 Vehicles │  │  4 Fog Nodes │  │ Cloud Server │          │
│  │  Task Gen    │  │  Task Queue  │  │  Task Queue  │          │
│  │  DQN Agent1  │  │  DQN Agent2  │  │  Batch Exec  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  • Task offloading decisions (Agent1)                           │
│  • Network routing decisions (Agent2)                           │
│  • SDN controller optimization                                  │
│  • TOF broker classification                                    │
│  • Handoff prediction & execution                               │
└───────────────┬─────────────────────────────────────┬───────────┘
                │                                     │
                └─────────┬───────────────┬───────────┘
                          │               │
         ┌────────────────↓───┐  ┌───────↓──────────────┐
         │    PostgreSQL      │  │      Redis (opt)    │
         │  • metrics_history │  │  • Live state cache │
         │  • task_events     │  │  • Connection state │
         │  • runtime_logs    │  │  • Vehicle positions│
         └────────────────────┘  └────────────────────┘
```

## Modules

### Core Simulation (`simulation/`)

- **runner.py** - SimPy simulation engine
- **env.py** - Environment orchestrator

### Agents (`agents/`)

- **agent1.py** - Task placement DQN (device/fog/cloud decision)
- **agent2.py** - Network routing DQN (SDN optimization)
- **dqn.py** - DQN neural network implementation

### Optimization (`optimizer/`)

- **nsga2_mmde.py** - MMDE-NSGA-II multi-objective optimizer
- Balances: latency, energy, deadline compliance

### Task Routing (`broker/`)

- **tof_broker.py** - TOF framework for task classification
- **tof_roles.py** - Vehicle & Fog broker roles

### Network Intelligence (`sdn/`)

- **controller.py** - SDN controller
- Preinstall optimization for high-priority tasks
- Reactive routing adjustment

### Mobility (`mobility/`)

- **handoff.py** - Trajectory prediction & handoff logic
- Proactive task migration between fog zones

### Storage (`storage/`)

- **data_store.py** - Redis + PostgreSQL facade
- Async batch writer for history
- Real-time state caching

### Visualization (`visualization/`)

- **api_server.py** - REST API endpoints
- **websocket_server.py** - Live metrics streaming
- **map_viz_model.py** - Map state generation (vehicles, connections, handoffs)

### Frontend (`frontend/`)

- **Dashboard.jsx** - Main dashboard
- **SystemExplorer.jsx** - System metrics observer
- **VehicleTrajectoryPanel.jsx** - Per-vehicle trajectory details
- **ConnectionsMonitor.jsx** - Network connection visualization

## Data Flow

### Task Creation → Execution

```
Vehicle (T=0.1s) generates task
    ↓
Agent1 decides: LOCAL/FOG-A/FOG-B/CLOUD
    ↓
Transmission (+ latency)
    ↓
Target node executes task
    ↓
Result returned to vehicle
    ↓
Metrics recorded (latency, energy, deadline_met)
```

### Fog-to-Fog Handoff

```
Vehicle in FOG-A coverage zone with pending task
    ↓
Trajectory predictor: T_exit = (distance to boundary) / (vehicle speed)
    ↓
If T_exit < T_execution: Send task to FOG-B proactively
    ↓
Task migrates: FOG-A → FOG-B during vehicle transition
    ↓
Handoff recorded in metrics
```

### Routing Optimization

```
Agent2 observes SDN state (congestion, latency)
    ↓
Decides: reactive routing OR preinstall high-priority lane
    ↓
SDN controller applies flow rules
    ↓
Reduces packet drops and latency
```

## Configuration

### FOG Network Topology

```python
FOG_NODES = {
    'A': {'pos': (150, 400), 'mips': 2000},  # Southwest
    'B': {'pos': (850, 400), 'mips': 2000},  # Southeast
    'C': {'pos': (350, 750), 'mips': 2000},  # Northwest
    'D': {'pos': (650, 200), 'mips': 2000},  # Northeast
}
```

### Performance Parameters

```
N_VEHICLES=50                    # Vehicle count
TASK_RATE_HZ=10                 # Tasks per second per vehicle
FOG_MIPS=2000                   # Fog processing power
CLOUD_MIPS=8000                 # Cloud processing power
FOG_COVERAGE_RADIUS=250         # Meters
TOTAL_DEADLINE_MS=200           # Task deadline
EC_THRESHOLD=1.0                # TOF classification threshold
```

## Execution Flow

1. **Bootstrap Phase** (0-10s)
    - Load CARLA trajectories
    - Run NSGA-II for baseline solutions
    - Pretrain agents on expert labels

2. **Warm-up Phase** (10-60s)
    - Stabilize vehicle movement patterns
    - Prime task queues
    - Initialize fog node loads

3. **Simulation Phase** (60-600s)
    - Real-time task offloading
    - Agent decision-making
    - Metrics collection

4. **Evaluation Phase**
    - Compare against baselines
    - Statistical analysis
    - Generate thesis results

## Key Metrics

| Metric                | Computation                                          |
| --------------------- | ---------------------------------------------------- |
| Deadline Success Rate | (tasks_deadline_met / total_tasks) × 100             |
| Avg Latency           | sum(latencies) / task_count                          |
| Avg Energy            | sum(energies) / task_count                           |
| Handoff Success       | (successful_handoffs / total_handoff_attempts) × 100 |
| SDN Preinstall Hit    | (preinstall_successful / preinstall_attempts) × 100  |

## Performance Targets

| Baseline           | Success % | Latency (ms) | Energy (J) |
| ------------------ | --------- | ------------ | ---------- |
| Pure NSGA-II (B1)  | 47%       | 167          | 0.25       |
| TOF+NSGA-II (B2)   | 68%       | 205          | 0.19       |
| TOF+MMDE (B3)      | 80%       | 163          | 0.16       |
| **Proposed (DQN)** | **>85%**  | **<80**      | **<0.12**  |

---

See [BASELINES.md](./BASELINES.md) for algorithm explanations.
