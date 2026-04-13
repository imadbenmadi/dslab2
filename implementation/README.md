# Smart City Vehicular Task Offloading System (Istanbul Urban Network)

**IoT–Fog–Cloud task offloading for vehicular object detection** using a hybrid of **TOF-broker classification**, **NSGA-II multi-objective optimization**, and **Deep Q-Network (DQN)** agents.

This README merges the content previously split across `PROJECT_SUMMARY.txt` and `explanation.md` into a single, coherent technical document.

---

## Contents

1. [Executive summary](#executive-summary)
2. [System architecture](#system-architecture)
3. [Task model (YOLO-style DAG)](#task-model-yolo-style-dag)
4. [Core algorithms](#core-algorithms)
5. [Real-world datasets (synthetic generators)](#real-world-datasets-synthetic-generators)
6. [Project structure](#project-structure)
7. [Quick start (offline pre-training)](#quick-start-offline-pre-training)
8. [Pre-training & validation](#pre-training--validation)
9. [Module reference (examples)](#module-reference-examples)
10. [Configuration](#configuration)
11. [Metrics](#metrics)
12. [Expected results (targets)](#expected-results-targets)
13. [Implementation status (accurate to this repo)](#implementation-status-accurate-to-this-repo)
14. [Next steps](#next-steps)
15. [Troubleshooting](#troubleshooting)
16. [References](#references)
17. [License](#license)

---

## Executive summary

This project models **smart-city vehicular object detection** as a **multi-step DAG** that must meet a strict end-to-end deadline (default: **200ms**). Vehicles produce tasks at camera rate, and the system decides where to execute offloadable DAG steps:

- **IoT layer:** vehicles
- **Fog layer:** 4 edge nodes (Istanbul districts)
- **Cloud layer:** central server

Key idea: split steps into **boulders** vs **pebbles** using TOF (execution-cost threshold), then route pebbles using **NSGA-II** and train a DQN (Agent 1) via **behavioral cloning**.

---

## System architecture

### 3-tier computing stack

```
IoT (Vehicles)
  ↓  4G/5G link
Fog (4 nodes)
  ↓  backbone
Cloud (1 node)
```

### Istanbul topology (from `config.py`)

- Fog-A: Besiktas at (200, 500)
- Fog-B: Sisli at (500, 200)
- Fog-C: Kadikoy at (800, 500)
- Fog-D: Uskudar at (500, 800)

Coverage radius: 250m (grid is 1000m × 1000m).

---

## Task model (YOLO-style DAG)

Object detection is modeled as a 5-step pipeline (see `config.py -> DAG_STEPS`):

1. Capture + compress (device)
2. Pre-process
3. Feature extract
4. Object classify
5. Alert generate

End-to-end requirement: `TOTAL_DEADLINE_MS = 200`.

---

## Core algorithms

### 1) TOF Broker (boulder / pebble classification)

The TOF broker computes **execution cost**:

```
EC = MI / FOG_MIPS   (seconds)
```

Classification rule (default threshold: `EC_THRESHOLD = 1.0`):

- If `EC ≥ 1.0s` → **boulder** → route to **cloud**
- Else → **pebble** → optimize offloading among fog/cloud actions

Implementation: `broker/tof_broker.py`.

### 2) Multi-objective optimization (NSGA-II)

For pebbles, NSGA-II optimizes two objectives:

1. Minimize **energy**
2. Minimize **latency**

Decision variables: per-step discrete action in `{Fog-A, Fog-B, Fog-C, Fog-D, Cloud}`.

Implementation: `optimizer/nsga2_mmde.py`.

### 3) Agent 1 (DQN) — task placement

- State: 13-dimensional vector built in `optimizer/nsga2_mmde.py::build_state_from_step()`
- Action space: 5 discrete destinations (Fog-A/B/C/D or Cloud)
- Offline pre-training: behavioral cloning from NSGA-II knee-point solution

Implementation: `agents/agent1.py` and `agents/dqn.py`.

### 4) Agent 2 (DQN) — SDN routing (scaffold)

Agent 2 is implemented as a DQN policy with a routing action space:

`PRIMARY, ALT1, ALT2, VIP_RESERVE, BEST_EFFORT`

Implementation: `agents/agent2.py`.

### 5) Mobility + handoff prediction

The trajectory predictor estimates:

- `T_exit`: time until a vehicle leaves the current fog coverage
- `T_exec`: execution time under fog load

Mode selection:

- `DIRECT` if `T_exec < T_exit`
- else `PROACTIVE`

Implementation: `mobility/handoff.py`.

---

## Real-world datasets (synthetic generators)

This repository integrates “real-world inspired” datasets via generators in `datasets.py`:

### CARLA-like trajectories

- Generates waypoints sampled at 10Hz on a 1000m × 1000m grid
- Exports to: `results/carla_trajectories.csv`

### CRAWDAD-like bandwidth traces

- Generates time-series bandwidth for `urban_4g`, `edge_wifi`, and `backbone`
- Exports to: `results/network_bandwidth.csv`

### YOLOv5-like latency benchmarks

`datasets.py` contains a benchmark table for YOLOv5 variants (CPU/GPU/Edge TPU) used to parameterize task generation.

---

## Project structure

```
implementation/
├── config.py
├── main.py
├── datasets.py
│
├── environment/
│   ├── task.py
│   ├── vehicle.py
│   ├── fog_node.py
│   ├── cloud.py
│   └── city.py
│
├── broker/
│   └── tof_broker.py
│
├── optimizer/
│   └── nsga2_mmde.py
│
├── agents/
│   ├── dqn.py
│   ├── agent1.py
│   └── agent2.py
│
├── mobility/
│   └── handoff.py
│
├── simulation/
│   ├── runner.py
│   └── env.py
│
├── baselines/
│   ├── baseline1.py
│   ├── baseline2.py
│   └── baseline3.py
│
├── sdn/
│   └── controller.py
│
└── results/
    ├── metrics.py
    ├── plots.py
    ├── carla_trajectories.csv
    └── network_bandwidth.csv
```

---

## Quick start (offline pre-training)

### Install

```bash
cd implementation
pip install -r requirements.txt
```

### Run offline pre-training

```bash
python main.py
```

What it does:

1. Generates CARLA-like trajectories and exports CSV
2. Generates bandwidth traces and exports CSV
3. Runs NSGA-II batches on realistic task samples
4. Produces training pairs and pre-trains Agent 1

---

## Pre-training & validation

### NSGA-II offline batches

The offline pre-training loop in `main.py` runs for `n_batches` (default: 50). Each batch builds a small set of pebble steps (currently capped to 10) and runs NSGA-II to produce a knee-point solution.

Training pairs:

- Approx. `n_batches × N_steps_per_batch`
- With the current defaults in `main.py`, this is typically around `50 × 10 = 500` pairs.

### Behavioral cloning (Agent 1)

After pairs are generated, Agent 1 is trained with supervised learning (`CrossEntropyLoss`) for a small number of epochs (default in `main.py`: 3).

Sanity checks included in the current pipeline:

- CSV exports are created under `results/`
- The optimizer runs end-to-end and returns Pareto solutions
- Agent 1 can train on the extracted (state, action) pairs

---

## Module reference (examples)

### Run TOF classification on a DAG task

```python
from broker.tof_broker import TOFBroker
from environment.task import generate_dag_task

task = generate_dag_task(task_id="t1", vehicle_id="vehicle_000", sim_time=0.0, spatial_tag={})
broker = TOFBroker()
result = broker.process_dag(task)
print(len(result["boulders"]), len(result["pebbles"]))
```

### Run NSGA-II optimization and extract training pairs

```python
import numpy as np
from optimizer.nsga2_mmde import run_nsga2_mmde, extract_training_pairs
from environment.task import DAGStep
from config import FOG_MIPS

fog_states = {"A": 0.3, "B": 0.4, "C": 0.35, "D": 0.25, "bandwidth_util": 0.5}
pebble_steps = [
  DAGStep(step_id=3, MI=2000, in_KB=50, out_KB=30, name="Feature", deadline_ms=80),
]
pebble_steps[0].ec = pebble_steps[0].MI / FOG_MIPS

pareto = run_nsga2_mmde(pebble_steps, fog_states)
pairs = extract_training_pairs(pebble_steps, fog_states, pareto)
print(pairs[0]["state"].shape, pairs[0]["action"])
```

### Use Agent 1 to select an offloading action

```python
from agents.agent1 import Agent1

agent = Agent1()
action = agent.select_action(pairs[0]["state"])
print("action:", action)
```

---

## Configuration

Key parameters live in `config.py`. Common knobs:

- Compute: `FOG_MIPS`, `CLOUD_MIPS`
- Network: `BANDWIDTH_MBPS`, `FOG_FOG_BW`, `FOG_CLOUD_BW`, `WAN_LATENCY_MS`, `G5_LATENCY_MS`
- Optimization: `NSGA_POP_SIZE`, `NSGA_GENS`, `NSGA_BATCH_SIZE`, `N_OFFLINE_BATCHES`
- Simulation: `SIM_DURATION_S`, `N_VEHICLES`, `TASK_RATE_HZ`

For faster runs, reduce `NSGA_POP_SIZE`, `NSGA_GENS`, and the `n_batches` argument passed to `run_offline_pretraining()` in `main.py`.

---

## Metrics

Collected metrics are defined in `results/metrics.py` (`SimMetrics`):

- Avg / P95 latency (ms)
- Avg / total energy (J)
- Feasibility rate (deadline met fraction)
- Handoff success rate (when simulated)
- Fog utilization
- SDN preinstall hit rate
- Boulder rate

---

## Expected results (targets)

The following are _target outcomes after the full end-to-end simulation, baselines, and evaluation pipeline are implemented_:

| System               | Avg latency | Feasibility | Energy | Handoff success |
| -------------------- | ----------: | ----------: | -----: | --------------: |
| Baseline 1 (NSGA-II) |      ~850ms |        ~45% | ~0.28J |            ~51% |
| Baseline 2 (TOF)     |      ~620ms |        ~62% | ~0.22J |            ~54% |
| Baseline 3 (MMDE)    |      ~480ms |        ~74% | ~0.19J |            ~57% |
| Proposed system      |  ~210–280ms |     ~88–93% | ~0.16J |         ~91–95% |

---

## Implementation status (accurate to this repo)

This section reflects the current code in this repository (some modules are scaffolds/placeholders).

### Implemented (Week 1 core)

- ✅ Configuration (`config.py`)
- ✅ DAG task definition (`environment/task.py`)
- ✅ TOF broker classification (`broker/tof_broker.py`)
- ✅ NSGA-II optimizer + training-pair extraction (`optimizer/nsga2_mmde.py`)
- ✅ DQN network + replay buffer (`agents/dqn.py`)
- ✅ Agent 1 & Agent 2 DQN implementations (`agents/agent1.py`, `agents/agent2.py`)
- ✅ Handoff predictor + HTB buffer (`mobility/handoff.py`)
- ✅ Metrics container (`results/metrics.py`)
- ✅ Offline pre-training pipeline + dataset exports (`main.py`, `datasets.py`)

### Partially implemented / scaffolds

- ◻ Fog node queueing: `environment/fog_node.py` (`process_task` is not implemented)
- ◻ Cloud processing: `environment/cloud.py` (`process_task` is not implemented)
- ◻ SimPy integration: `simulation/runner.py` is a placeholder
- ◻ Gymnasium env: `simulation/env.py` is a minimal stub
- ◻ Baselines: `baselines/baseline1.py`, `baseline2.py`, `baseline3.py` are placeholders
- ◻ Plots: `results/plots.py` is a placeholder
- ◻ SDN controller abstraction: `sdn/controller.py` has stubbed methods

---

## Next steps

Planned work (from the project summary):

1. Implement SimPy event loop (`simulation/runner.py`)
2. Implement fog/cloud processing and queueing (`environment/fog_node.py`, `environment/cloud.py`)
3. Implement baselines and evaluation (`baselines/`, `results/plots.py`)
4. Integrate SDN controller and connect Agent 2 to routing decisions (`sdn/controller.py`)

---

## Troubleshooting

| Issue                 | Fix                                                      |
| --------------------- | -------------------------------------------------------- |
| `ModuleNotFoundError` | `pip install -r requirements.txt`                        |
| Slow optimization     | Reduce `NSGA_GENS` / `NSGA_POP_SIZE` / number of batches |
| CSV export fails      | Ensure `implementation/results/` exists                  |

---

## References

- CARLA: https://github.com/carla-simulator/carla
- YOLOv5: https://github.com/ultralytics/yolov5
- CRAWDAD: https://crawdad.org/

---

## License

MIT License (see repository/license information).
