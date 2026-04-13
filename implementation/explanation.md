# Smart City Vehicular Task Offloading System — Deep Project Explanation

This document is the **single, accurate, “deep explanation”** of the runnable code inside this repository (primarily the `implementation/` folder).

It covers:

1. what the system simulates,
2. how the **unified (monolithic)** runtime works end-to-end (the mode used by the React dashboard today),
3. how the **distributed microservices** variant is structured (NATS + mTLS),
4. what every major module does,
5. how to run, test, and troubleshoot.

If you only want to _run_ it, start with **“Running the system”**.

---

## 1. What this project is

This project is a **smart city simulation** for **vehicular task offloading** in an IoT–Fog–Cloud hierarchy.

Vehicles generate compute workloads that represent a simplified **object detection pipeline** (modeled as a small DAG). The system decides where to execute each offloadable stage:

- locally on the vehicle,
- on a nearby fog node (edge server),
- or in the cloud.

The goal is to balance multiple constraints:

- **end-to-end latency** (deadline-driven),
- **energy cost** (transmit + compute),
- **network conditions** (bandwidth/latency),
- **mobility** (handoffs between fog coverage zones).

### The two runtime “modes” in this repo

There are two parallel implementations:

1. **Unified runtime (recommended for the dashboard):** one Python process runs simulation + Flask API + WebSocket.
    - Entry point: `app.py` (`python app.py proposed`).
    - This is the most complete and integrated path.

2. **Distributed runtime (experimental):** vehicle, fog, and cloud run as separate processes and exchange telemetry via NATS (with optional TLS/mTLS).
    - Entry point: `python -m services.orchestrator`.
    - This is a structural foundation (service boundaries, telemetry topics, cert tooling). Some parts are intentionally simplified and a few components need alignment.

---

## 2. Repo layout (what to read first)

Most runnable code lives in `implementation/`.

Key folders:

- `app.py` — unified orchestrator (simulation + API + WebSocket).
- `config.py` — all tunable parameters loaded from `.env`.
- `docs/` — user-facing documentation (quickstart, architecture, database, config).
- `frontend/` — React dashboard.
- `environment/` — domain objects: city/topology, vehicles, tasks.
- `broker/` — TOF classification and role wrappers.
- `optimizer/` — NSGA-II + MMDE mutation implementation.
- `agents/` — DQN Agent1 (placement) and Agent2 (routing/SDN).
- `mobility/` — handoff prediction + buffers.
- `sdn/` — SDN controller abstraction.
- `framework/` — shared contracts, messaging semantics, policy, security registry.
- `storage/` — Redis + PostgreSQL/TimescaleDB data store facade.
- `visualization/` — Flask routes and WebSocket server used by the UI.
- `services/` + `infrastructure/` — distributed service implementations + NATS/mTLS tooling.

For a guided tour, also see `docs/INDEX.md`.

---

## 3. The simulated world (domain model)

### 3.1 City + fog topology

The simulation uses a **1000m × 1000m** coordinate plane to represent an Istanbul-like urban region.

Fog nodes are fixed anchors defined in `config.py`:

- 4 fog nodes (`A`, `B`, `C`, `D`) with positions (`pos`), names, and initial loads.
- A coverage radius `FOG_COVERAGE_RADIUS` models which vehicles are “in range”.

### 3.2 Vehicles

The system models a fleet of `N_VEHICLES` vehicles. In the unified runtime, vehicles are updated in a loop and the backend maintains:

- current position and heading,
- derived connectivity to fog nodes,
- handoff events when vehicles cross coverage boundaries.

### 3.3 Task = a DAG pipeline

Workload is modeled as a 5-stage pipeline in `config.py` (`DAG_STEPS`) and constructed by `environment/task.py` (`generate_dag_task`).

Each stage is a `DAGStep` with:

- compute demand (`MI`, million instructions),
- input/output sizes (`in_KB`, `out_KB`),
- a name and per-step soft deadline (`deadline_ms`).

Stage 1 is marked to run on device (`runs_on: device`). Other stages are offloadable.

The task has a global constraint `TOTAL_DEADLINE_MS`.

### 3.4 Compute + network model

The model is intentionally simple but consistent:

- execution time is proportional to `MI / MIPS` (with load adjustments in some components),
- transmission time is computed from payload size and bandwidth,
- cloud access includes a WAN latency term (`WAN_LATENCY_MS`).

All the defaults (and their `.env` keys) are in `config.py`.

---

## 4. The “intelligence stack” (how decisions are made)

This project combines **heuristics**, **offline optimization**, and **reinforcement learning**.

### 4.1 TOF broker (boulder vs pebble)

The Task Offloading Framework (TOF) is implemented in `broker/tof_broker.py`.

It computes an execution-cost proxy for each offloadable step:

```
EC(step) = step.MI / FOG_MIPS   (seconds)
```

Classification rule:

- if `EC > EC_THRESHOLD` → **boulder** (immediately routed to cloud),
- else → **pebble** (eligible for fog/optimized placement).

This is a fast way to avoid wasting fog resources on “too heavy” compute.

There are also role wrappers in `broker/tof_roles.py`:

- `TofLiteVehicleBroker` — vehicle-side quick classification,
- `TofFogBroker` — fog authoritative classification.

### 4.2 Offline multi-objective optimization (NSGA-II + MMDE)

`optimizer/nsga2_mmde.py` defines a Pymoo optimization problem where each gene corresponds to a placement decision for a pebble step:

- action 0..3 → fog nodes A..D
- action 4 → cloud

The optimizer returns a Pareto front and selects a “knee point” by normalized distance-to-utopia.

This file also provides helper functions to turn optimization outcomes into **supervised labels** (training pairs) for agents.

Important note: there are baseline scripts under `baselines/` that reference older interfaces (they call `run_nsga2_mmde` with different parameters). The conceptual idea is correct, but those scripts may require small alignment work to run end-to-end.

### 4.3 DQN Agent 1 (placement)

`agents/agent1.py` implements Agent1:

- **state dimension:** 13 (`AGENT1_STATE_DIM`)
- **actions:** 5 (`AGENT1_ACTION_DIM`) = fog A..D + cloud
- **policy:** epsilon-greedy over a feed-forward network (`agents/dqn.py`)

Agent1 can be pre-trained via **behavioral cloning** using labels extracted from the TOF+MMDE-NSGA-II pipeline. The code enforces provenance by requiring training pairs with `source == "tof-mmde-nsga2"`.

### 4.4 DQN Agent 2 (routing / SDN)

`agents/agent2.py` implements Agent2:

- **state dimension:** 15 (`AGENT2_STATE_DIM`)
- **actions:** 5 = primary path, alternates, VIP lane reservation, best-effort

It supports “pre-installed” rules (0ms overhead) and reactive controller routing (8–15ms overhead).

In the unified runtime, this agent is paired with the SDN abstraction in `sdn/controller.py`.

### 4.5 Mobility + handoff prediction

`mobility/handoff.py` provides:

- `TrajectoryPredictor.compute_t_exit(...)` — estimates time until a vehicle exits a fog coverage zone,
- `compute_t_exec(...)` — estimates execution time under current load,
- `select_mode(...)` — chooses `DIRECT` vs `PROACTIVE` based on `t_exec` and `t_exit`,
- `HTBBuffer` — a handoff buffer holding in-flight task results for vehicles that temporarily disconnect.

This enables proactive offloading and continuity under mobility.

---

## 5. Unified runtime (monolithic) — the actual end-to-end system

### 5.1 Why it exists

The unified runtime is the most “complete” version because it keeps all modules in one process:

- simulation loop,
- agents,
- optimization/bootstrap,
- storage facade,
- REST API,
- WebSocket streaming to the dashboard.

This eliminates distributed systems complexity while still letting you evaluate algorithms.

### 5.2 Entrypoint

Run from `implementation/`:

```bash
python app.py proposed
```

`app.py` builds an instance of `UnifiedSmartCityApp` and wires together:

- `visualization/api_server.py` (Flask routes),
- `visualization/websocket_server.py` (WS streaming),
- runtime routes in `app_runtime/api_routes.py` (start/stop/retrain/control),
- internal metrics/logging in `results/`.

### 5.3 Eventing inside the unified runtime

Even though it’s one process, it models “distributed” behavior using framework primitives:

- `framework/contracts.py` — typed event envelopes + validation
- `framework/messaging.py` — at-least-once semantics + dedup patterns
- `framework/policy.py` — policy/control plane bundle and sync clients
- `framework/security.py` — identity registry

This is useful because you can later map the same logical contracts onto a real broker (NATS/MQTT).

### 5.4 What the frontend talks to

The dashboard uses:

- REST endpoints on `http://127.0.0.1:5000/api/...`
- WebSocket on `ws://127.0.0.1:8765`

The actual routes are defined mainly in `visualization/api_server.py` and extended by `app_runtime/api_routes.py`.

### 5.5 Unified runtime walkthrough (what happens each “tick”)

At a high level, the unified runtime (`UnifiedSmartCityApp` in `app.py`) runs a loop that continuously:

1. **advances simulation time** and updates vehicle positions,
2. **generates DAG tasks** (via `environment/task.py`),
3. **classifies steps** using TOF (vehicle-lite and/or authoritative broker),
4. chooses a placement + routing strategy depending on `system_type` (`proposed`, `baseline1`, `baseline2`, `baseline3`),
5. simulates network + compute delay, then records:
    - completion latency
    - energy proxy
    - deadline success
    - handoff + migration counters
6. updates “observability snapshots” used by the UI:
    - metrics window
    - logic snapshot (policy, bus stats, buffers)
    - map state (vehicles, fog nodes, connections, handoffs)
7. pushes a `SystemMetrics` payload to the WebSocket broadcast queue.

The key point is: **the dashboard is not a replay tool**. It’s reading live state that is computed in-process by the unified runtime.

### 5.6 Metrics: what’s tracked and why

The runtime exposes metrics in two ways:

- **streaming (WebSocket):** fast live metrics for UI responsiveness.
- **history (storage):** a bounded history window in memory and optional persistence via `storage/data_store.py`.

The WebSocket model is the `SystemMetrics` dataclass in `visualization/websocket_server.py`. It includes:

- top-level performance (success rate, avg latency, throughput, task count)
- node loads (fog1..fog4 + cloud)
- network utilization + congestion proxy
- agent latencies (agent1/agent2 decision overhead proxies)
- mobility metrics (handoff count, task migrations)
- optional `map_snapshot` and `agent_snapshot` for richer UI panels

### 5.7 WebSocket schema (what the UI receives)

Every broadcast is JSON of the form:

```json
{
    "type": "metrics",
    "data": {
        "timestamp": "...",
        "simulationTime": 123.4,
        "successRate": 82.1,
        "avgLatency": 140.2,
        "taskCount": 5000,
        "throughput": 9000.0,
        "devices": {
            "fog1": 0.4,
            "fog2": 0.6,
            "fog3": 0.5,
            "fog4": 0.3,
            "cloud": 0.2
        },
        "network": { "bandwidthUsed": 55.0, "congestionPoints": 2 },
        "agents": { "agent1Latency": 8.2, "agent2Latency": 2.0 },
        "agentDetails": { "...": "..." },
        "handoff": { "count": 3, "taskMigrations": 1 },
        "map": {
            "vehicles": [],
            "fogNodes": [],
            "connections": [],
            "handoffs": []
        }
    }
}
```

This is generated by `SystemMetrics.to_dict()`.

### 5.8 API surface (most important endpoints)

Core endpoints are in `visualization/api_server.py`:

- `GET /api/health` — health + storage status
- `GET /api/status` — simulation running state + system type
- `GET /api/metrics/current` — last metric sample
- `GET /api/metrics/history?limit=50` — metric history window
- `GET /api/evaluation/summary` — summary stats with bootstrap CIs over the history window
- `POST /api/simulation/start` — start the simulation worker (supports `{"systemType": "proposed"}`)
- `POST /api/simulation/stop`
- `POST /api/simulation/reset`
- `GET /api/logic/snapshot` — internal pipeline snapshot
- `GET /api/tasks/recent?limit=100`
- `GET /api/logs/recent?limit=100`

Runtime/control endpoints are added by `app_runtime/api_routes.py`:

- `POST /api/retrain` — triggers a background retraining thread
- `GET /api/training-status`
- `GET /api/map/live` — returns the current map state
- `GET /api/agents/analytics` — current + recent agent stats and bootstrap info
- `GET|POST /api/control/policy` — read/update policy rules
- `POST /api/control/features` — feature flags
- `POST /api/control/fleet` — fleet tuning controls
- `GET /api/control/bus` — event bus status + recent messages

If you’re debugging UI/backend integration, these are the endpoints to hit first.

---

## 6. Distributed runtime (microservices) — structure and current state

### 6.1 Why it exists

The `services/` + `infrastructure/` folders are a “distributed architecture path”:

- vehicle-service generates telemetry,
- fog-service makes decisions and publishes routing/decision events,
- cloud-service exposes API + WS and aggregates telemetry.

### 6.2 Entrypoint

```bash
python -m services.orchestrator
```

This will:

- generate certificates into `certs/` (via `infrastructure/cert_manager.py`),
- start `services.vehicle_service`, `services.fog_service`, `services.cloud_service`.

You also need a running NATS broker at `localhost:4222`.

### 6.3 Telemetry topics

Topic mapping is centralized in `infrastructure/nats_bus.py` (event bridge).
Examples:

- `VehicleTaskSubmitted` → `telemetry.vehicle.task-submitted`
- `FogDecisionMade` → `telemetry.fog.decision`
- `TaskCompleted` → `telemetry.task.completed`

### 6.4 Current limitations (important)

The microservices path is **experimental** and intentionally simplified. A few mismatches exist today:

- Some payload shapes published over NATS don’t exactly match the dataclasses in `framework/contracts.py`.
- `cloud_service.py` broadcasts a plain dict to `WebSocketServer.broadcast_metrics(...)`, but the WS implementation was designed around a `SystemMetrics` object.
- `services/vehicle_service.py` uses `TrajectoryGenerator(...)` with a signature that does not match the current `datasets.TrajectoryGenerator` constructor.
- TLS/mTLS configuration may require running a TLS-enabled NATS server (a plain `nats:latest` container may not be sufficient).

These are fixable, but this document keeps the explanation truthful to the current code.

---

## 7. Storage + observability

### 7.1 Storage facade

`storage/data_store.py` provides a unified “data access layer” for:

- Redis (live state cache)
- PostgreSQL/TimescaleDB (historical metrics)

The system can run without full DB infra for basic simulation, but the dashboard/history features benefit from it.

### 7.2 Logs and results

Runtime logs and structured events are written under `results/logs/`.

If you see issues, start by checking:

- `results/logs/events.jsonl`
- application logs created by `results/logging_utils.py`

---

## 8. Configuration (.env + config.py)

### 8.1 How config is loaded

`config.py` calls `load_dotenv()` at import time and then reads typed values via `settings/env_loader.py`.

That means:

- the working directory matters (it looks for `.env` in the current directory),
- environment variables override defaults.

### 8.2 Recommended workflow

```bash
copy .env.example .env
```

Then adjust values like:

- `N_VEHICLES`, `TASK_RATE_HZ`, `SIM_DURATION_S`, `WARMUP_S`
- `FOG_MIPS`, `CLOUD_MIPS`, `EC_THRESHOLD`
- bootstrap knobs: `ENABLE_BOOTSTRAP_PRETRAIN`, `BOOTSTRAP_*`

---

## 9. Running the system

### 9.1 Unified (recommended)

From `implementation/`:

```bash
pip install -r requirements.txt
python app.py proposed
```

Then, in another terminal:

```bash
cd frontend
npm install
npm start
```

Open:

- Dashboard: `http://localhost:3000`
- API health: `http://127.0.0.1:5000/api/health`
- WebSocket: `ws://127.0.0.1:8765`

### 9.2 Optional: start Redis + TimescaleDB

```powershell
./scripts/start_infra.ps1
```

Or via Docker Compose:

```bash
docker compose up -d redis timescaledb
```

### 9.3 Distributed (experimental)

Start NATS (plain TCP):

```bash
docker run -d --name nats -p 4222:4222 nats:latest
```

Then:

```bash
python -m services.orchestrator
```

If TLS is enabled in your service configuration, you may need to run a TLS-enabled NATS server.

---

## 10. Testing

Tests are under `tests/` (unittest).

Run from `implementation/`:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

There is also a quick manual verification script:

```bash
python test_system.py
```

---

## 11. Troubleshooting (practical)

### 11.1 Frontend shows blanks / no metrics

- Confirm backend is running (`/api/health`).
- Confirm WebSocket port `8765` is open.
- Check `results/logs/` for runtime exceptions.

### 11.2 “.env changes don’t apply”

`config.py` loads `.env` at import time. Make sure you:

- run Python from the `implementation/` directory, and
- restart the backend after changing `.env`.

### 11.3 Distributed mode can’t connect to NATS

- Ensure NATS is running on `127.0.0.1:4222`.
- If `enable_tls=True`, you need a TLS-enabled NATS listener.

---

## 12. References (conceptual background)

- SimPy: https://simpy.readthedocs.io/
- Pymoo / NSGA-II: https://pymoo.org/
- NATS: https://docs.nats.io/

---

### Bottom line

If your goal is to **demonstrate the full system with the React dashboard**, use the **unified runtime** (`python app.py proposed`).

If your goal is to **study the distributed architecture direction**, use `services/` + `infrastructure/` (and expect to do some interface alignment work as noted above).
