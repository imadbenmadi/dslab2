# Broker Module - Task Classification

## Purpose

Implements **TOF (Task Offloading Characterization) Broker** - an intelligent task classifier that decides whether tasks should go to the **Cloud (Boulder)** or be optimized locally/in fog **(Pebble)**.

## The Classification Problem

Not all tasks are created equal. Some tasks:

- **Need high compute** (large ML models, data processing) → Go to Cloud
- **Need low latency** (real-time detection, alerts) → Go to Fog/Local

The TOF Broker automatically categorizes which is which based on **execution time**.

## How It Works

### The Classification Metric: EC (Execution Cost)

```
EC = Task MI / Fog Node MIPS

EC = (Million Instructions) / (2000 MIPS)
```

### Classification Rule

```python
if EC >= 1.0 second:
    Task = "Boulder" → Send to Cloud
    (Too heavy for fog, guaranteed in cloud)
else:
    Task = "Pebble" → Optimize placement
    (Light enough for fog, optimize allocation)
```

### Example

```
YOLOv5 small model:
- MI: 500 million instructions
- Fog MIPS: 2000
- EC = 500/2000 = 0.25 seconds < 1.0s → PEBBLE
- Decision: Try fog first, optimize placement

Complex data processing:
- MI: 3000 million instructions
- Fog MIPS: 2000
- EC = 3000/2000 = 1.5 seconds > 1.0s → BOULDER
- Decision: Send directly to cloud
```

## Why We Used TOF Broker

### Problem It Solves

**Without TOF:** System wastes compute trying to handle everything locally

```
All 10,000 tasks per second
  ↓
Try all in fog (57% fail deadline)
  ↓
Retry heavy ones in cloud (too late, already missed deadline)
  ↓
Cascading failures
```

**With TOF:** Route intelligently from start

```
10,000 tasks/second
  ↓
TOF classifies into 2 streams
  ↓
Heavy (30%): Immediately to cloud ✓
Light (70%): Optimize for fog
  ↓
81% deadline success (Baseline 3)
```

### Performance Impact

| System        | Deadline Success | Avg Latency |
| ------------- | ---------------- | ----------- |
| No classifier | 47% (baseline1)  | 167ms       |
| With TOF      | 68% (baseline2)  | 205ms\*     |
| With TOF+MMDE | 81% (baseline3)  | 163ms       |

_Higher latency because some tasks wisely routed to cloud get better completion rate_

## How Used in Full System

### Integration Points

1. **Task Generation** (environment/task.py)
    - Each task MI calculated based on workload
    - EC computed automatically

2. **Baselines** (baselines/)
    - Baseline 2: Uses classification to split tasks
    - Baseline 3: Enhanced version with MMDE

3. **Agents** (agents/)
    - Proposed system: Learns when to override TOF decisions
    - "Boulder" override: Some "boulders" handled in fog if deadline tight
    - "Pebble" promotion: Some light tasks sent to cloud if fog congested

4. **Evaluation**
    - Dashboard shows boulder/pebble split
    - Metrics track classification accuracy

## Files

- **tof_broker.py** (47 lines)
    - `classify()` - Categorize individual task
    - `process_dag()` - Classify 5-step task pipeline
    - Statistics tracking (boulder count, pebble count)

## Real-World Tuning

The **EC_THRESHOLD = 1.0s** is tunable in `config.py`:

```python
# Conservative: Send more to cloud
EC_THRESHOLD = 0.8  # Lower threshold

# Aggressive: Keep more in fog
EC_THRESHOLD = 1.2  # Higher threshold
```

Recommended: **1.0s** (proven in system testing)

## Classification Examples

### Light Tasks (Pebble) - Good for Fog

```
YOLOv5 object detection:
  EC = 0.25s → PEBBLE
  Route: Fog optimization applies
  Benefit: Low latency, uses local compute

Small data filtering:
  EC = 0.1s → PEBBLE
  Route: Can process on device
  Benefit: Minimal transmission delay
```

### Heavy Tasks (Boulder) - Need Cloud

```
Data center analytics:
  EC = 2.5s → BOULDER
  Route: Straight to cloud
  Benefit: Won't bottleneck fog nodes

Deep learning model inference (large):
  EC = 1.8s → BOULDER
  Route: Cloud's high compute capacity
  Benefit: Reliable completion
```

## Key Insight

**TOF Broker improves baseline by 21%** (47% → 68% deadline success) because it prevents misdirected tasks. By applying **domain knowledge** (execution time prediction), the system makes smarter initial decisions that adaptation (DQN) can then refine online.

This is why the full system uses **TOF + MMDE + DQN** together - each layer adds value.
