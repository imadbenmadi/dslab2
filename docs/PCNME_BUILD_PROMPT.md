# PCNME Framework — Full Implementation Prompt
# Predictive Cloud-Native Mobile Edge
# Task Offloading Framework for IoT–Fog–Cloud Systems
# ============================================================
#
# READ THIS FIRST
# ---------------
# This prompt is for an AI coding agent. It describes a complete,
# production-quality framework to build from scratch. The framework
# must be general-purpose (not Istanbul-specific), professionally
# engineered, and come with a real case study that exercises every
# component. Read every section before writing a single line of code.
# ============================================================

---

## WHAT YOU ARE BUILDING

A **general-purpose task offloading framework** for IoT–Fog–Cloud systems called
**PCNME (Predictive Cloud-Native Mobile Edge)**. The framework must be usable by
any researcher or engineer who wants to deploy intelligent task offloading in any
smart city, industrial IoT, or vehicular edge computing environment — not just Istanbul.

The framework has two halves:

1. **The Framework itself** — a Python library that any user can configure and run
   on their own topology, task types, and mobility traces.

2. **A Case Study application** — a concrete Istanbul vehicular object detection
   scenario that demonstrates the framework end-to-end, with a full React dashboard
   showing every metric, chart, and live system state.

The user should be able to:
- Install the framework
- Point it at their own config (fog topology, task types, mobility data)
- Run NSGA-II pre-training offline
- Deploy both DRL agents
- Watch everything live in the dashboard
- Export results as CSV and charts

---

## EXISTING CODEBASE CONTEXT

The developer already has a working prototype with this structure:

```
implementation/
├── app.py                    # Unified orchestrator (Flask + WebSocket + sim loop)
├── config.py                 # All parameters via .env
├── broker/                   # TOF-Broker + role wrappers
├── optimizer/                # NSGA-II + MMDE (pymoo-based)
├── agents/                   # DQN Agent1 (placement) + Agent2 (SDN routing)
│   └── dqn.py                # Shared DQN network architecture
├── mobility/                 # Trajectory predictor + NTB/HTB buffers
├── sdn/                      # SDN controller abstraction
├── environment/              # City, vehicles, DAG tasks
├── storage/                  # Redis + TimescaleDB facade
├── visualization/            # Flask API + WebSocket server
├── framework/                # Contracts, messaging, policy, security
├── results/                  # Logging, metrics, CSV export
└── frontend/                 # React dashboard (exists but needs full rebuild)
```

The prototype runs with `python app.py proposed` and serves a React frontend.
The WebSocket broadcasts SystemMetrics JSON every tick. The REST API has endpoints
for start/stop/reset/retrain/status/metrics/map/agents.

**Key things the prototype does correctly:**
- TOF-Broker EC classification (boulders → cloud, pebbles → optimizer)
- NSGA-II + MMDE with pymoo, knee-point selection, (state,action) pair extraction
- DQN Agent1 (13-dim state, 5 actions) with behavioral cloning pre-training
- DQN Agent2 (15-dim state, 5 actions) for SDN routing
- T_exit proactive handoff per DAG step
- NTB/HTB dual-buffer reactive fallback
- Aggregator for pebble avalanche prevention
- Redis + TimescaleDB storage facade

**What needs to be built/rebuilt:**
- Framework abstraction layer (make it topology-agnostic, not Istanbul-hardcoded)
- Real dataset integration (see DATA section below)
- Proper framework CLI and configuration system
- Complete React dashboard (current one is incomplete — rebuild it fully)
- Istanbul case study as a packaged example
- Professional README and usage documentation

---

## STACK — DO NOT DEVIATE

### Backend
```
Python 3.11+
fastapi                  # Replace Flask — async, better WebSocket support
uvicorn                  # ASGI server
websockets               # WebSocket broadcasting
pymoo>=0.6               # NSGA-II with custom MMDE operator
torch>=2.1               # DQN agents (CPU is fine, CUDA optional)
numpy, pandas, scipy     # Data handling and statistics
redis                    # Live state cache (required)
asyncpg + timescaledb    # Time-series metrics storage (optional but include)
pydantic>=2              # Config validation and API schemas
python-dotenv            # Environment loading
httpx                    # Async HTTP client for health checks
structlog                # Structured logging
pytest                   # Tests
```

### Frontend
```
React 18 + TypeScript
Vite                     # Build tool (not CRA)
Recharts                 # All charts and plots
Leaflet + react-leaflet  # Live map visualization
Tailwind CSS             # Styling
Zustand                  # State management
React Query (TanStack)   # API data fetching
```

### Infrastructure
```
Redis 7                  # Required
TimescaleDB (PostgreSQL 15 + timescale extension)   # For metric history
Docker + docker-compose  # For Redis and TimescaleDB
```

---

## REAL DATA — USE THESE SOURCES

The framework must support real datasets, not purely synthetic mobility.
For the Istanbul case study specifically, use:

### 1. Mobility traces — Istanbul IETT Bus GPS
- **Source:** Istanbul Metropolitan Municipality open data portal
  - URL: https://data.ibb.gov.tr/dataset/iett-otobus-seferleri
  - Format: CSV with columns: trip_id, vehicle_id, timestamp, lat, lon
  - If the live API is unavailable, generate synthetic traces that match
    real Istanbul street topology using the OSM road network for Istanbul
    (bounding box: lat 40.85–41.20, lon 28.50–29.50)

### 2. Road network — OpenStreetMap
- Use the `osmnx` Python library to download the Istanbul road network
- Constrain vehicle movement to actual road segments
- `osmnx.graph_from_bbox(41.20, 40.85, 29.50, 28.50, network_type='drive')`

### 3. Traffic density — time-of-day patterns
- Morning rush: 07:30–09:30 (vehicle arrival rate × 2.5)
- Evening rush: 17:00–19:30 (vehicle arrival rate × 2.2)
- Football match spikes (Besiktas JK, Galatasaray, Fenerbahce):
  schedule match events on Wednesday and weekend evenings
  with Besiktas zone density × 1.8 during match hours

### 4. Task workload — realistic object detection parameters
Use published benchmark numbers from YOLO inference literature:
- ResNet-50 feature extraction: 4.1 GFLOPS → scale to MI appropriately
- MobileNetV3 (lightweight): 0.22 GFLOPS
- YOLOv8n (nano): 8.7 GFLOPs per image at 640×640

The framework must allow users to plug in their own task profiles via config.

### 5. Framework synthetic generator (for non-Istanbul use)
Include a `pcnme.datasets.synthetic` module that generates:
- Random Waypoint mobility on user-defined grids
- Poisson task arrival processes
- Configurable DAG structures with user-specified MI and data sizes

---

## FRAMEWORK STRUCTURE — BUILD THIS EXACTLY

```
pcnme/                              # The installable Python package
│
├── __init__.py                     # Public API surface
├── core/
│   ├── config.py                   # Pydantic BaseSettings — all parameters
│   ├── topology.py                 # FogNode, CloudNode, NetworkLink definitions
│   ├── task.py                     # DAGTask, DAGStep, TaskBatch
│   ├── vehicle.py                  # Vehicle, SpatialTag, MobilityTrace
│   └── enums.py                    # OffloadTarget, HandoffMode, TaskClass
│
├── broker/
│   ├── tof_broker.py               # TOFBroker: EC classification, boulder/pebble
│   └── aggregator.py               # Aggregator: avalanche prevention, super-tasks
│
├── optimizer/
│   ├── nsga2_mmde.py               # NSGA-II + MMDE operator (pymoo)
│   ├── problem.py                  # TaskOffloadingProblem (pymoo Problem subclass)
│   ├── pretrain.py                 # Offline pre-training pipeline
│   └── pareto.py                   # Knee-point selection, Pareto analysis utilities
│
├── agents/
│   ├── networks.py                 # DQN, DuelingDQN network architectures
│   ├── replay.py                   # PrioritizedReplayBuffer
│   ├── agent1.py                   # Agent1: task placement (DQN)
│   └── agent2.py                   # Agent2: SDN routing (DQN)
│
├── mobility/
│   ├── predictor.py                # TrajectoryPredictor, T_exit computation
│   ├── handoff.py                  # HandoffManager, mode selection
│   └── buffers.py                  # NTBBuffer, HTBBuffer, CentralTracker
│
├── sdn/
│   ├── controller.py               # SDNController: OpenFlow abstraction
│   └── rules.py                    # FlowRule, RuleCache, VIPLane
│
├── simulation/
│   ├── engine.py                   # SimulationEngine: main event loop (asyncio)
│   ├── clock.py                    # SimulationClock: sim time vs wall time
│   └── metrics.py                  # MetricsCollector, running statistics
│
├── datasets/
│   ├── iett.py                     # Istanbul IETT bus GPS loader and processor
│   ├── osm.py                      # OSM road network loader (osmnx)
│   ├── synthetic.py                # Synthetic mobility and task generators
│   └── loader.py                   # DatasetLoader: unified interface
│
├── storage/
│   ├── redis_store.py              # RedisStore: live state cache
│   ├── timescale_store.py          # TimescaleStore: metric history
│   └── store.py                    # DataStore: unified facade
│
├── api/
│   ├── app.py                      # FastAPI application factory
│   ├── routes/
│   │   ├── simulation.py           # /api/simulation/* endpoints
│   │   ├── metrics.py              # /api/metrics/* endpoints
│   │   ├── agents.py               # /api/agents/* endpoints
│   │   ├── map.py                  # /api/map/live endpoint
│   │   ├── training.py             # /api/training/* endpoints
│   │   └── control.py              # /api/control/* endpoints
│   └── websocket.py                # WebSocket broadcaster
│
├── cli/
│   └── main.py                     # pcnme CLI (click-based)
│
└── utils/
    ├── logging.py                  # structlog setup
    └── math.py                     # Helper functions (normalise, clip, etc.)

case_studies/
└── istanbul/
    ├── __init__.py
    ├── config.yaml                 # Istanbul-specific parameter overrides
    ├── topology.py                 # 4 fog nodes at Besiktas/Sisli/Kadikoy/Uskudar
    ├── tasks.py                    # Object detection DAG definition
    ├── mobility.py                 # IETT data loader + OSM road network
    └── run.py                      # python case_studies/istanbul/run.py

dashboard/                          # React + TypeScript frontend
├── src/
│   ├── App.tsx
│   ├── store/
│   │   └── useStore.ts             # Zustand store
│   ├── hooks/
│   │   ├── useWebSocket.ts         # WebSocket connection + message handling
│   │   └── useMetrics.ts           # React Query hooks for REST endpoints
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   └── TopBar.tsx
│   │   ├── map/
│   │   │   ├── CityMap.tsx         # Leaflet map: fog zones, vehicles, connections
│   │   │   └── MapLegend.tsx
│   │   ├── metrics/
│   │   │   ├── KPICards.tsx        # Success rate, avg latency, energy, throughput
│   │   │   ├── LatencyChart.tsx    # Real-time rolling latency line chart
│   │   │   ├── EnergyChart.tsx     # Energy per task over time
│   │   │   ├── FogLoadChart.tsx    # Stacked bar: CPU load per fog node
│   │   │   ├── ParetoChart.tsx     # Pareto front scatter plot
│   │   │   └── HandoffChart.tsx    # Handoff success rate over time
│   │   ├── agents/
│   │   │   ├── Agent1Panel.tsx     # Agent1: Q-values, epsilon, loss curve
│   │   │   ├── Agent2Panel.tsx     # Agent2: flow rules, VIP hits, overhead
│   │   │   └── TrainingPanel.tsx   # Pre-training progress, behavioral cloning loss
│   │   ├── pipeline/
│   │   │   ├── PipelineView.tsx    # Live task flow: device→fog→cloud
│   │   │   ├── DAGViewer.tsx       # Current DAG task with step statuses
│   │   │   └── BrokerStats.tsx     # Boulder/pebble split, EC distribution
│   │   └── control/
│   │       ├── SimControl.tsx      # Start/stop/reset, system type selector
│   │       ├── ConfigPanel.tsx     # Live parameter adjustment
│   │       └── ExportPanel.tsx     # Download CSV, charts as PNG
│   └── pages/
│       ├── Dashboard.tsx           # Main overview page
│       ├── FrameworkPage.tsx       # Framework status, topology, config
│       ├── CaseStudyPage.tsx       # Istanbul case study: all charts
│       └── AnalyticsPage.tsx       # Deep dive: Pareto analysis, agent analytics
│
├── package.json
├── tsconfig.json
└── vite.config.ts

docker/
├── docker-compose.yml              # Redis + TimescaleDB
├── redis/
│   └── redis.conf
└── timescale/
    └── init.sql                    # Schema creation

tests/
├── unit/
│   ├── test_broker.py
│   ├── test_optimizer.py
│   ├── test_agents.py
│   ├── test_mobility.py
│   └── test_api.py
└── integration/
    └── test_simulation_loop.py

README.md
pyproject.toml                      # Package metadata + dependencies
.env.example
```

---

## SYSTEM PARAMETERS — USE THESE EXACT VALUES

```python
# pcnme/core/config.py (Pydantic BaseSettings)

# Compute
FOG_MIPS: int = 2000          # MIPS per fog node
CLOUD_MIPS: int = 8000        # MIPS cloud (4× faster)
EC_THRESHOLD: float = 1.0     # Boulder/pebble boundary (seconds)
Q_MAX: int = 50               # Max pebble queue before aggregator triggers

# Network
BANDWIDTH_MBPS: float = 100.0   # IoT → fog upload bandwidth
FOG_CLOUD_BW: float = 1000.0   # Fog → cloud backbone (Mbps)
FOG_FOG_BW: float = 100.0      # Fog → fog inter-node (Mbps)
WAN_LATENCY_MS: float = 30.0   # Fog → cloud propagation delay
G5_LATENCY_MS: float = 2.0     # Vehicle → fog 5G latency
SDN_PREINSTALL_MS: float = 0.0 # Pre-installed rule overhead
SDN_REACTIVE_MS: float = 12.0  # Reactive new-flow overhead (8–15ms range)

# Fog coverage
FOG_COVERAGE_RADIUS: float = 250.0  # metres

# NSGA-II + MMDE
NSGA_POP_SIZE: int = 100
NSGA_GENS: int = 200
MMDE_F: float = 0.5         # Differential scaling factor
MMDE_CR: float = 0.9        # Crossover rate
NSGA_BATCH_SIZE: int = 100
N_OFFLINE_BATCHES: int = 1000

# DQN Agent 1 (placement)
AGENT1_STATE_DIM: int = 13
AGENT1_ACTION_DIM: int = 5    # Fog A, B, C, D, Cloud
AGENT1_HIDDEN: list = [256, 128]
AGENT1_LR: float = 0.001
AGENT1_GAMMA: float = 0.95
AGENT1_EPSILON_START: float = 0.30
AGENT1_EPSILON_END: float = 0.05
AGENT1_EPSILON_DECAY: int = 10000
AGENT1_BATCH_SIZE: int = 64
AGENT1_BUFFER_SIZE: int = 50000
AGENT1_TARGET_UPDATE: int = 1000

# DQN Agent 2 (SDN routing)
AGENT2_STATE_DIM: int = 15
AGENT2_ACTION_DIM: int = 5    # Primary, Alt1, Alt2, VIP, BestEffort
AGENT2_HIDDEN: list = [256, 128]
AGENT2_LR: float = 0.001
AGENT2_GAMMA: float = 0.95
AGENT2_EPSILON_START: float = 0.25
AGENT2_EPSILON_END: float = 0.05
AGENT2_EPSILON_DECAY: int = 8000
AGENT2_BATCH_SIZE: int = 64
AGENT2_BUFFER_SIZE: int = 50000
AGENT2_TARGET_UPDATE: int = 1000

# Rewards
AGENT1_REWARD_LATENCY: float = 0.5
AGENT1_REWARD_ENERGY: float = 0.3
AGENT1_REWARD_VIOLATION: float = 0.2
AGENT1_DEADLINE_PENALTY: float = 10.0
AGENT2_REWARD_DELIVERY: float = 0.5
AGENT2_REWARD_DELAY: float = 0.3
AGENT2_REWARD_OVERHEAD: float = 0.2
AGENT2_PACKET_DROP_PENALTY: float = 50.0
AGENT2_PREINSTALL_BONUS: float = 0.3

# Simulation
N_VEHICLES: int = 50
VEHICLE_SPEED_MEAN: float = 60.0   # km/h
VEHICLE_SPEED_STD: float = 15.0
TASK_RATE_HZ: float = 10.0
SIM_DURATION_S: float = 600.0
WARMUP_S: float = 60.0
RANDOM_SEED: int = 42
N_RUNS: int = 5
```

---

## THE FIVE-STEP OBJECT DETECTION DAG (Istanbul Case Study)

```python
DAG_STEPS = {
    1: {"MI": 20,   "in_KB": 8192, "out_KB": 200,  "name": "Capture+Compress",  "runs_on": "device"},
    2: {"MI": 200,  "in_KB": 200,  "out_KB": 50,   "name": "Pre-process",       "deadline_ms": 30},
    3: {"MI": 2000, "in_KB": 50,   "out_KB": 30,   "name": "Feature Extract",   "deadline_ms": 80},
    4: {"MI": 8000, "in_KB": 30,   "out_KB": 5,    "name": "Object Classify",   "deadline_ms": 150},
    5: {"MI": 50,   "in_KB": 5,    "out_KB": 1,    "name": "Alert Generate",    "deadline_ms": 200},
}
TOTAL_DEADLINE_MS = 200
```

EC values: Step1=0.01 (device), Step2=0.10 (pebble), Step3=1.00 (borderline pebble),
Step4=4.00 (boulder → cloud), Step5=0.025 (pebble).

---

## ISTANBUL TOPOLOGY (Case Study Fog Nodes)

```python
FOG_NODES = {
    "A": {"pos": (200, 500), "name": "Besiktas",  "lat": 41.0428, "lon": 29.0066, "load": 0.30},
    "B": {"pos": (500, 200), "name": "Sisli",     "lat": 41.0618, "lon": 28.9877, "load": 0.45},
    "C": {"pos": (800, 500), "name": "Kadikoy",   "lat": 40.9833, "lon": 29.0500, "load": 0.35},
    "D": {"pos": (500, 800), "name": "Uskudar",   "lat": 41.0237, "lon": 29.0150, "load": 0.40},
}
CLOUD = {"name": "Istanbul Cloud", "lat": 41.0150, "lon": 28.9500, "MIPS": 8000}
```

---

## CORE ALGORITHMS — IMPLEMENT THESE EXACTLY

### TOF-Broker
```python
def classify(step: DAGStep, fog_mips: int, threshold: float) -> Literal["boulder", "pebble"]:
    ec = step.MI / fog_mips
    return "boulder" if ec >= threshold else "pebble"
```

Boulders are immediately routed to cloud. Pebbles enter the optimizer pipeline.
When pebble queue depth > Q_MAX, Aggregator bundles them into a super-task
and routes via SDN VIP lane — bypassing optimization entirely.

### MMDE Mutation (inside pymoo NSGA-II)
```python
class MMDEMutation(Operator):
    def _do(self, problem, X, **kwargs):
        n, n_var = X.shape
        X_mut = X.copy()
        for i in range(n):
            idxs = np.random.choice([j for j in range(n) if j != i], 3, replace=False)
            r1, r2, r3 = X[idxs[0]], X[idxs[1]], X[idxs[2]]
            for k in range(n_var):
                if np.random.rand() < self.CR:
                    diff = int(round(self.F * (r2[k] - r3[k])))
                    X_mut[i, k] = np.clip(int(r1[k]) + diff, 0, problem.n_actions - 1)
        return X_mut
```

### T_exit Formula
```python
def compute_t_exit(vehicle_pos, vehicle_speed_ms, vehicle_heading_deg, fog_pos, fog_radius):
    dx = fog_pos[0] - vehicle_pos[0]
    dy = fog_pos[1] - vehicle_pos[1]
    dist = math.sqrt(dx**2 + dy**2)
    if dist >= fog_radius:
        return 0.0
    heading_rad = math.radians(vehicle_heading_deg)
    vx = vehicle_speed_ms * math.cos(heading_rad)
    vy = vehicle_speed_ms * math.sin(heading_rad)
    radial_x, radial_y = -dx/dist, -dy/dist
    v_closing = vx * radial_x + vy * radial_y
    if v_closing <= 0:
        return float('inf')
    return (fog_radius - dist) / v_closing
```

### Agent 1 Reward
```python
def compute_reward(latency_ms, energy_j, deadline_ms, is_safety_critical=False):
    norm_lat = min(latency_ms / deadline_ms, 3.0)
    norm_eng = min(energy_j / 0.1, 3.0)
    violation = 1.0 if latency_ms > deadline_ms else 0.0
    penalty = 10.0 if is_safety_critical else 1.0
    return -0.5*norm_lat - 0.3*norm_eng - 0.2*violation*penalty
```

### Agent 2 Reward
```python
def compute_reward(delivery_ratio, delay_ms, overhead_ms, packet_drop, preinstall_hit):
    R = 0.5*delivery_ratio - 0.3*min(delay_ms/50, 1.0) - 0.2*min(overhead_ms/15, 1.0)
    if packet_drop: R -= 50.0
    if preinstall_hit: R += 0.3
    return R
```

---

## WEBSOCKET MESSAGE SCHEMA

Every 500ms the backend broadcasts this JSON to all connected dashboard clients:

```json
{
  "type": "metrics",
  "data": {
    "timestamp": "2026-04-13T20:00:00.000Z",
    "simulationTime": 123.4,
    "successRate": 87.3,
    "avgLatency": 142.1,
    "p95Latency": 198.4,
    "avgEnergy": 0.047,
    "taskCount": 12450,
    "throughput": 10200,
    "boulderRate": 0.22,
    "pebbleRate": 0.78,
    "handoffSuccessRate": 91.4,
    "fogUtilBalance": 0.08,
    "sdnPreinstallHitRate": 0.79,
    "devices": {
      "fog_A": 0.42, "fog_B": 0.61, "fog_C": 0.38, "fog_D": 0.40, "cloud": 0.21
    },
    "network": {
      "bandwidthUtil": 0.55,
      "congestionPoints": 2,
      "sdnRulesActive": 14,
      "vipLanesOpen": 1
    },
    "agents": {
      "agent1": {
        "epsilon": 0.12,
        "loss": 0.043,
        "avgQValue": -1.82,
        "stepsSinceUpdate": 47,
        "actionDistribution": [0.31, 0.18, 0.27, 0.15, 0.09]
      },
      "agent2": {
        "epsilon": 0.08,
        "loss": 0.031,
        "preinstallHits": 142,
        "reactiveHits": 37,
        "avgOverheadMs": 1.4
      }
    },
    "training": {
      "phase": "online",
      "pretrainComplete": true,
      "pretrainLoss": 0.021,
      "bcPairsUsed": 98420,
      "onlineUpdates": 5230
    },
    "handoff": {
      "total": 187,
      "proactive": 162,
      "reactive": 25,
      "failed": 0,
      "avgMigrationMs": 11.2
    },
    "map": {
      "vehicles": [
        {"id": "v-01", "lat": 41.038, "lon": 29.002, "speed": 68, "heading": 90,
         "connectedFog": "A", "taskStatus": "processing", "handoffMode": "direct"}
      ],
      "fogNodes": [
        {"id": "A", "name": "Besiktas", "lat": 41.0428, "lon": 29.0066,
         "load": 0.42, "queueDepth": 7, "radiusM": 250}
      ],
      "connections": [
        {"from": "v-01", "to": "fog_A", "type": "5G", "active": true}
      ],
      "handoffEvents": [
        {"vehicleId": "v-03", "fromFog": "A", "toFog": "B",
         "mode": "proactive", "tExitS": 3.6}
      ]
    },
    "pareto": {
      "front": [
        {"energy": 0.041, "latency": 138.2},
        {"energy": 0.047, "latency": 128.5},
        {"energy": 0.053, "latency": 119.7}
      ],
      "kneePoint": {"energy": 0.047, "latency": 128.5},
      "hypervolume": 0.724,
      "generation": 200
    }
  }
}
```

---

## REST API ENDPOINTS — IMPLEMENT ALL OF THESE

```
GET  /api/health                          Health check + storage status
GET  /api/status                          Simulation state, system type, uptime

POST /api/simulation/start                Body: {"systemType": "proposed", "config": {...}}
POST /api/simulation/stop
POST /api/simulation/reset
GET  /api/simulation/config               Returns current full config

GET  /api/metrics/current                 Latest metric snapshot
GET  /api/metrics/history?limit=200       Rolling window of snapshots
GET  /api/metrics/export?format=csv       Download all metrics as CSV

GET  /api/evaluation/summary              Aggregate stats with 95% bootstrap CIs

GET  /api/map/live                        Current map state (vehicles, fog, connections)

GET  /api/agents/status                   Both agents: weights loaded, training phase
GET  /api/agents/analytics                Detailed: loss curves, Q-values, epsilon
POST /api/agents/retrain                  Trigger background behavioral cloning
GET  /api/agents/training-status          Pre-train progress (0–100%)

GET  /api/optimizer/pareto                Latest Pareto front + knee point
GET  /api/optimizer/history               Pareto front per generation (for animation)

GET  /api/broker/stats                    Boulder/pebble counts, EC distribution
GET  /api/sdn/rules                       Active OpenFlow rules + VIP lanes
GET  /api/mobility/handoffs               Recent handoff events with mode breakdown

GET  /api/pipeline/snapshot               Internal state: queues, buffers, decisions
GET  /api/tasks/recent?limit=100          Last N completed tasks with all fields
GET  /api/logs/recent?limit=100           Structured log entries

POST /api/control/config                  Hot-reload specific config parameters
POST /api/control/scenario                Switch case study scenario
```

---

## DASHBOARD PAGES — BUILD ALL FOUR

### Page 1: Dashboard (main overview)
- **Top bar:** simulation time, elapsed wall time, status indicator (running/stopped/training)
- **Control strip:** Start / Stop / Reset buttons, system type dropdown
- **KPI cards row:** Success Rate %, Avg Latency ms, Avg Energy J, Throughput tasks/s, Handoff Success %
- **Live map (left 60%):** Leaflet map of Istanbul. Show:
  - Fog node circles with radius 250m, colour-coded by CPU load (grey scale)
  - Vehicle dots moving in real time, colour by handoff mode (direct=white, proactive=light grey, HTB=dark)
  - Animated connection lines between vehicles and their fog node
  - Handoff arrows when a vehicle crosses a zone boundary
  - Cloud shown as a server icon top-right
- **Fog load bars (right 40%):** Horizontal bar chart, one per fog node + cloud, updating live
- **Network panel:** Bandwidth utilization gauge, congestion point count, active SDN rules, VIP lanes

### Page 2: Framework Status
- **Topology panel:** Static diagram of the fog-cloud topology with configured parameters
- **Config table:** All active parameters, editable fields with live hot-reload
- **Pipeline diagram:** Flowchart: Vehicle → TOF-Broker → [Boulder→Cloud | Pebble→Optimizer→Agent1] → Fog/Cloud → Result → Vehicle
- **Broker stats:** Boulder vs pebble pie chart, EC value histogram, avalanche events counter
- **Aggregator status:** Queue depth gauge vs Q_MAX, super-tasks sent count

### Page 3: Case Study — Istanbul
- **Section header:** Istanbul Vehicular Object Detection case study description
- **Latency over time:** Line chart, rolling 60s window, with 95% CI band
- **Energy over time:** Same style
- **Pareto front chart:** Scatter plot of current Pareto front (energy vs latency), knee point highlighted as filled circle, utopia point shown as crosshair
- **DAG step breakdown:** Stacked bar: per-step average latency contribution (Step 1 device, Step 2 fog, Step 3 fog/cloud, Step 4 cloud, Step 5 fog)
- **Handoff analysis:** Pie chart: proactive vs reactive vs HTB fallback. Line chart: handoff success rate over time. Histogram: T_exit distribution at time of decision
- **Traffic heatmap:** Istanbul map with vehicle density overlay, updating per tick. Rush hours and match events clearly visible

### Page 4: Agent Analytics
- **Agent 1 panel:**
  - Epsilon decay curve (current position highlighted)
  - Training loss curve (behavioral cloning loss then online loss, two phases shown)
  - Q-value distribution per action (box plot, one box per fog node + cloud)
  - Action distribution bar chart: how often each fog node or cloud is selected
  - State feature importance (computed as variance of Q-value gradient per state dim)
- **Agent 2 panel:**
  - Pre-install hit rate vs reactive hit rate line chart
  - Controller overhead histogram (ms per flow)
  - Active SDN rules by path (stacked bar, colour by priority class)
  - Reward curve over time
- **Training panel:**
  - Behavioral cloning phase: loss per epoch, number of (state,action) pairs used
  - Online phase: cumulative reward, steps completed
  - Timeline showing offline→online transition point

---

## FRAMEWORK CLI — IMPLEMENT THIS

```bash
# Install
pip install -e .

# Run the Istanbul case study (downloads OSM data on first run)
pcnme run --case-study istanbul --mode proposed --duration 600

# Run the framework on a custom config
pcnme run --config my_city.yaml --duration 600

# Pre-train agents offline only
pcnme pretrain --config my_city.yaml --batches 1000 --output weights/

# Load pre-trained weights and run
pcnme run --config my_city.yaml --weights weights/ --duration 600

# Export results
pcnme export --format csv --output results/
pcnme export --format json --output results/

# Start just the API server (attach your own frontend)
pcnme serve --port 8000

# Validate a config file
pcnme validate --config my_city.yaml

# Run tests
pcnme test
```

---

## HOW TO MAKE IT FRAMEWORK-AGNOSTIC (NOT ISTANBUL-HARDCODED)

The framework core (`pcnme/`) must have zero references to Istanbul, districts,
or any specific topology. All scenario-specific details live in `case_studies/`.

A user creates a new case study by:
1. Creating `case_studies/my_city/config.yaml` with their fog topology
2. Defining their DAG task structure in `case_studies/my_city/tasks.py`
3. Providing a mobility trace (CSV with columns: timestamp, vehicle_id, lat, lon)
   or using the synthetic generator

The framework loads everything through the `DatasetLoader` and `Topology` abstractions.
The optimizer, agents, and mobility layer are topology-agnostic by design.

Example custom config:
```yaml
# case_studies/smart_factory/config.yaml
fog_nodes:
  - id: "F1"
    name: "Assembly Line A"
    pos: [100, 100]
    lat: 0.0
    lon: 0.0
    mips: 3000
    initial_load: 0.25
  - id: "F2"
    name: "Warehouse B"
    pos: [400, 100]
    lat: 0.0
    lon: 0.0
    mips: 2500
    initial_load: 0.35
fog_coverage_radius: 150
dag_steps:
  - id: 1
    name: "Sensor read"
    MI: 50
    in_KB: 10
    out_KB: 5
    runs_on: device
  - id: 2
    name: "Quality check"
    MI: 500
    in_KB: 5
    out_KB: 2
    deadline_ms: 50
n_vehicles: 20
task_rate_hz: 5
```

---

## REAL TRAINING — NOT FAKE

The agents must actually train. Do not use placeholder loss values or mock updates.

### Behavioral cloning pre-training (Agent 1)
1. Run TOF-MMDE-NSGA-II on N_OFFLINE_BATCHES = 1000 synthetic batches
2. Each batch: 100 pebble tasks with randomized fog loads, EC values, vehicle speeds
3. Extract knee-point solution → (state_vector, action) pairs
4. Train DQN with CrossEntropyLoss(q_values, action_label)
5. Report loss per epoch. Stop when loss < 0.05 or after 20 epochs.

### Online DQN training (both agents)
1. Every completed task step → store (s, a, r, s', done) in PrioritizedReplayBuffer
2. After each step: sample batch of 64, compute TD targets, gradient update
3. Sync target network every 1000 steps
4. Log loss, Q-value mean, epsilon at each update

### Agent 2 pre-training
1. Generate synthetic Istanbul traffic patterns (rush hours, match nights)
2. Rule: if predicted_traffic > 0.7 and 3s ahead → action = VIP_RESERVE
3. Otherwise select best path based on simulated link utilizations
4. Use these synthetic decisions as behavioral cloning labels

---

## STORAGE SCHEMA

### Redis keys (live state)
```
pcnme:sim:state              # JSON: current simulation state
pcnme:sim:metrics:latest     # JSON: last SystemMetrics snapshot
pcnme:map:live               # JSON: current map state
pcnme:agents:status          # JSON: agent weights, epsilon, loss
pcnme:sdn:rules              # JSON: active OpenFlow rules
pcnme:htb:buffer             # JSON: pending handoff results by vehicle_id
```

### TimescaleDB tables
```sql
-- Metric time-series
CREATE TABLE metrics (
    time        TIMESTAMPTZ NOT NULL,
    sim_time    FLOAT,
    success_rate FLOAT,
    avg_latency  FLOAT,
    p95_latency  FLOAT,
    avg_energy   FLOAT,
    throughput   FLOAT,
    boulder_rate FLOAT,
    handoff_success_rate FLOAT,
    sdn_preinstall_rate FLOAT,
    fog_a_load   FLOAT,
    fog_b_load   FLOAT,
    fog_c_load   FLOAT,
    fog_d_load   FLOAT,
    cloud_load   FLOAT
);
SELECT create_hypertable('metrics', 'time');

-- Individual task completions
CREATE TABLE tasks (
    id          UUID PRIMARY KEY,
    time        TIMESTAMPTZ NOT NULL,
    vehicle_id  TEXT,
    step_id     INT,
    assigned_to TEXT,
    latency_ms  FLOAT,
    energy_j    FLOAT,
    deadline_ms FLOAT,
    deadline_met BOOLEAN,
    handoff_mode TEXT
);
SELECT create_hypertable('tasks', 'time');

-- Pareto front snapshots
CREATE TABLE pareto_snapshots (
    time        TIMESTAMPTZ NOT NULL,
    generation  INT,
    hypervolume FLOAT,
    front_json  JSONB,
    knee_energy FLOAT,
    knee_latency FLOAT
);
SELECT create_hypertable('pareto_snapshots', 'time');

-- Agent training log
CREATE TABLE agent_training (
    time        TIMESTAMPTZ NOT NULL,
    agent_id    TEXT,
    phase       TEXT,
    step        INT,
    loss        FLOAT,
    epsilon     FLOAT,
    avg_q_value FLOAT,
    reward      FLOAT
);
SELECT create_hypertable('agent_training', 'time');
```

---

## DOCKER COMPOSE — INCLUDE THIS

```yaml
# docker/docker-compose.yml
version: "3.9"

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./redis/redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf

  timescaledb:
    image: timescale/timescaledb:latest-pg15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: pcnme
      POSTGRES_PASSWORD: pcnme_secret
      POSTGRES_DB: pcnme
    volumes:
      - timescale_data:/var/lib/postgresql/data
      - ./timescale/init.sql:/docker-entrypoint-initdb.d/init.sql

volumes:
  redis_data:
  timescale_data:
```

---

## BUILD ORDER — FOLLOW THIS SEQUENCE

Do not jump ahead. Complete each phase before starting the next.

### Phase 1 — Core framework (no agents yet)
1. `pcnme/core/` — config, topology, task, vehicle, enums
2. `pcnme/broker/` — TOF-Broker + Aggregator
3. `pcnme/optimizer/` — NSGA-II + MMDE problem + pareto utilities
4. `pcnme/mobility/` — T_exit predictor + NTB/HTB buffers
5. `pcnme/sdn/` — SDN controller abstraction + rule cache
6. Unit tests for all of the above
7. **Checkpoint:** `pcnme pretrain --case-study istanbul` should run and produce
   Pareto fronts with correct knee-point selection. Verify with printed output.

### Phase 2 — Agents
8. `pcnme/agents/networks.py` — DQN network architectures
9. `pcnme/agents/replay.py` — prioritized replay buffer
10. `pcnme/agents/agent1.py` — placement DQN with behavioral cloning
11. `pcnme/agents/agent2.py` — SDN routing DQN
12. **Checkpoint:** behavioral cloning loss should drop below 0.05 in ≤20 epochs.
    Print loss per epoch to confirm.

### Phase 3 — Simulation engine + API
13. `pcnme/simulation/engine.py` — async event loop, one tick per 100ms sim time
14. `pcnme/simulation/metrics.py` — running statistics collector
15. `pcnme/api/app.py` — FastAPI app factory
16. `pcnme/api/routes/` — all REST endpoints
17. `pcnme/api/websocket.py` — broadcaster pushing SystemMetrics every 500ms
18. `pcnme/storage/` — Redis + TimescaleDB facade
19. **Checkpoint:** `pcnme run --case-study istanbul` should run for 60s and
    broadcast WebSocket messages. Verify with `wscat -c ws://localhost:8765`.

### Phase 4 — Istanbul case study + OSM data
20. `pcnme/datasets/osm.py` — download Istanbul OSM road network with osmnx
21. `pcnme/datasets/iett.py` — IETT GPS trace loader (or synthetic fallback)
22. `pcnme/datasets/synthetic.py` — rush hour + match night traffic patterns
23. `case_studies/istanbul/` — full case study package
24. **Checkpoint:** vehicles should follow Istanbul road geometry. Handoffs should
    occur more frequently during rush hour periods.

### Phase 5 — Dashboard
25. Scaffold React + TypeScript + Vite project in `dashboard/`
26. Implement WebSocket hook and Zustand store
27. Build Page 1: Dashboard (map + KPI cards + fog loads)
28. Build Page 2: Framework Status (topology + config + pipeline diagram)
29. Build Page 3: Case Study (all Istanbul-specific charts)
30. Build Page 4: Agent Analytics (training curves + Q-value analysis)
31. **Checkpoint:** All four pages render correctly with live data from the backend.
    No hardcoded values anywhere in the frontend — all data comes from the API or WebSocket.

### Phase 6 — Polish
32. CSV and PNG export endpoints
33. CLI (`pcnme` command) with all subcommands
34. `pyproject.toml` with correct dependencies
35. `.env.example` with all parameters documented
36. `README.md` — installation, quick start, CLI reference, case study walkthrough
37. Integration tests
38. **Final checkpoint:** run the complete system for 600s and produce a results
    export showing success rate > 85%, handoff success rate > 90%.

---

## QUALITY REQUIREMENTS

- No `time.sleep()` in the simulation loop. Use asyncio throughout.
- No hardcoded strings for fog node names or IDs anywhere in `pcnme/` core.
- Every REST endpoint returns proper HTTP status codes and Pydantic-validated responses.
- Every WebSocket message matches the schema in this document exactly.
- Logging uses structlog with JSON output to `results/logs/`.
- All floating point values in metrics are rounded to 3 decimal places before sending.
- The dashboard must be fully responsive and work at 1280×800 minimum resolution.
- No console.log statements in the final dashboard build.
- Unit test coverage for broker, optimizer, and mobility modules must be ≥ 80%.

---

## WHAT SUCCESS LOOKS LIKE

When the implementation is complete, a user should be able to:

```bash
# Clone repo
git clone <repo>
cd pcnme

# Start infrastructure
docker compose -f docker/docker-compose.yml up -d

# Install framework
pip install -e .

# Run the Istanbul case study
pcnme run --case-study istanbul --duration 600

# In another terminal, start the dashboard
cd dashboard && npm install && npm run dev

# Open http://localhost:5173 and see:
# - Vehicles moving on an Istanbul map
# - Fog node loads updating in real time
# - Pareto front forming on the Analytics page
# - Agent training curves showing convergence
# - Handoff events being handled proactively
# - Success rate > 85% after warmup

# Export results
pcnme export --format csv --output results/run_001/
```

A professor reviewing this should immediately understand:
1. What the framework does (from the dashboard)
2. How the intelligence works (from the Agent Analytics page)
3. That the results are real (from the TimescaleDB-backed metric history)
4. That it is a general framework (from the config system and case study separation)

---

## ONE FINAL INSTRUCTION

Do not simplify or stub anything. If a component is listed in this document,
implement it fully. The mock/placeholder pattern is the single most common
failure mode in academic software — it produces systems that look complete
on the dashboard but produce meaningless numbers.

The agents must actually learn. The optimizer must actually run NSGA-II.
The handoff predictor must actually compute T_exit from vehicle positions.
The TimescaleDB must actually store metric history. The OSM road network must
actually constrain vehicle movement.

This is a research framework. Every number it produces will be cited in a thesis.
Make it real.
