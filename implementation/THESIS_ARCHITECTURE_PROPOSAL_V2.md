# Thesis Architecture Proposal v2

## Predictive Cloud-Native Mobile Edge Optimized Task Offloading for Smart City Vehicular IoT Networks

Application domain: Autonomous and connected vehicles in Istanbul urban network.

This document defines the full proactive 3-tier IoT-Fog-Cloud architecture and maps it to the current implementation.

## 1. Application Scenario - Istanbul Smart Cars

The system targets a moving fleet of connected vehicles in dense Istanbul districts (Besiktas, Sisli, Kadikoy, Uskudar).

Key scenario parameters:

- Vehicles: 50-100
- Speed: 30-100 km/h
- Camera pipeline rate: 10 FPS
- Deadline: 200ms end-to-end
- Fog coverage radius: 250m
- Fog zones: 4 district-aligned nodes

Problem statement:

- Vehicles generate perception DAG workloads every 100ms.
- Vehicles are mobile, so fog assignment must account for zone exit time.
- Wrong assignment causes deadline misses or stale results.

## 2. DAG Pipeline and Partial Offloading

Each frame is a 5-step DAG:

- Step 1 (Capture/Compress): device-local
- Step 2 (Pre-process): pebble candidate
- Step 3 (Feature extraction): heavy pebble / borderline
- Step 4 (Object classification): boulder -> cloud
- Step 5 (Alert generation): light step, fog/device candidate

Execution cost model:

- EC = task_MI / fog_MIPS
- Boulders are rejected from fog optimization and escalated to cloud.

This creates partial offloading:

- Different DAG steps execute on different tiers.
- TOF broker decides per-step split before optimization.

## 3. Three-Tier System Architecture

### Layer 1 - IoT Vehicles

Vehicle daemon:

- Captures frames
- Builds DAG task
- Attaches spatial tag (vehicle_id, position, speed, heading, timestamp)
- Sends ingress to nearest fog

### Layer 2 - Fog (Application Logic)

Components:

- TOF Broker: pebble/boulder split
- Aggregator: queue pressure handling + super-task bundling
- RL Agent 1: compute placement policy
- Trajectory predictor: proactive handoff trigger
- NTB/HTB buffers: normal and handoff-priority queues

### Layer 2 - Fog (Network Logic)

Components:

- SDN Controller: global network view + OpenFlow rule execution
- RL Agent 2: proactive routing and lane reservation
- Traffic monitor: link load, queue depth, pending traffic forecasts

### Layer 3 - Cloud

Cloud responsibilities:

- Execute boulder steps and super-tasks
- Return results through fog for delivery
- Host analytics APIs and historical query endpoints

## 4. Offline Optimization + Online RL

### Offline

TOF-MMDE-NSGA-II generates Pareto-optimal supervision labels.

- MMDE mutation refines NSGA search quality.
- Knee-point selections become (state, action) labels.

### Online

Two DQN agents execute real-time policy decisions.

- Agent 1: task placement policy
- Agent 2: SDN routing policy

Behavioral cloning warm-start avoids cold-start instability.

## 5. Mobility and Proactive Handoff

Core formula:

- T_exit = (R_fog - dist(car, fog_center)) / v_closing

Decision logic:

- If T_exec < T_exit: direct mode
- If T_exec > T_exit: proactive migration / pre-spin
- If prediction fails: HTB fallback and delayed delivery

Per-step mobility awareness is applied at DAG step granularity, not whole-task granularity.

## 6. Data and Cloud-Native Persistence

### Live state plane (Redis)

- Current metrics and short-term feeds
- Low-latency UI read path

### Historical plane (Timescale/PostgreSQL)

- Metrics history
- Task event history
- Runtime structured logs
- Time-based indexes + vehicle-id index for fast window queries

### Write efficiency

- Background batch writer queues and flushes DB writes
- Reduces per-event write overhead under high traffic

## 7. API Surface for Historical Analytics

Implemented endpoints:

- GET /api/analytics/window?window=1h|24h
- GET /api/analytics/vehicle/<vehicle_id>?window=1h|24h&limit=200
- GET /api/health (includes storage backend connectivity status)

## 8. UI Mapping

Routes:

- /map: geographic runtime view
- /agents: RL observability
- /logic: system logic explorer + storage/analytics panels
- /thesis: thesis architecture explainer page

## 9. Baseline and Evaluation Strategy

Baselines:

- Baseline 1: plain NSGA-II
- Baseline 2: TOF + NSGA-II
- Baseline 3: TOF + MMDE-NSGA-II (no online RL)
- Proposed: full TOF-MMDE-NSGA-II + Agent1 + Agent2 + proactive handoff

Primary metrics:

- Average latency
- Deadline feasibility rate
- Energy consumption
- Handoff success rate
- SDN pre-install hit rate
- Fog utilization balance

## 10. Reproducibility

One-command infra startup:

- PowerShell: ./scripts/start_infra.ps1
- Docker Compose: docker compose up -d redis timescaledb

Enable backends in .env:

- ENABLE_REDIS_STATE=true
- ENABLE_POSTGRES_HISTORY=true

This proposal and implementation are aligned for thesis reporting and demo execution.
