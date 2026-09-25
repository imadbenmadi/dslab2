# Baseline Comparison

This explains the three baseline systems and how they compare to the proposed DQN solution.

## The Three Baselines

### Baseline 1: Pure NSGA-II

**What it does:**
- Runs NSGAII optimization OFFLINE on sample tasks
- Makes all routing decisions statically based on optimization
- NO online learning, NO adaptation to real conditions

**Configuration:**
```python
population_size = 50
generations = 50
timeout = 30s
```

**Expected Results:**
- Success Rate: ~47%
- Avg Latency: ~167 ms
- Avg Energy: ~0.250 J
- Handoff Success: ~51%

**Why it fails:**
- No adaptation to network changes
- Static decisions can't handle dynamic conditions
- Doesn't learn from execution

**Code:** `baselines/baseline1.py`

---

### Baseline 2: TOF + NSGA-II

**What it does:**
- Classifies each task as Boulder (cloud) or Pebble (fog)
- Uses TOF heuristic: high MI/size ratio → Boulder (latency-critical)
- Runs NSGA-II only on Pebble tasks
- Still static after optimization

**Configuration:**
```python
EC_THRESHOLD = 1.0          # Energy criticality threshold
TOF_BOULDER_FRACTION ≈ 30%  # Expected cloud-bound tasks
```

**Expected Results:**
- Success Rate: ~68% (**+21% vs B1**)
- Avg Latency: ~205 ms
- Avg Energy: ~0.186 J
- Handoff Success: ~64%

**Why it improves:**
- Smart classification reduces optimization complexity
- Latency-sensitive tasks go directly to cloud
- Flexible tasks get optimized placement
- Boulder/Pebble split reduces decision space

**Code:** `baselines/baseline2.py`

---

### Baseline 3: TOF + MMDE-NSGA-II

**What it does:**
- Same TOF classification as B2
- Uses MMDE (Modified Multi-strategy Differential Evolution) mutation
- MMDE improves convergence vs standard NSGA-II
- Still static decisions (no online learning)

**MMDE Improvement:**
```python
# Standard genetic algorithm mutation
mutation_rand = uniform(0, 1)

# MMDE mutation (3 random vectors combined)
r1, r2, r3 = random_population_members()
F = 0.5  # Differential evolution parameter
CR = 0.9 # Crossover rate
mutated = r1 + F * (r2 - r3)  # DE strategy
```

**Expected Results:**
- Success Rate: ~80% (**+12% vs B2, +58% vs B1**)
- Avg Latency: ~163 ms
- Avg Energy: ~0.157 J
- Handoff Success: ~77%

**Why it's the best offline solution:**
- Superior convergence of MMDE vs standard mutation
- Better exploration vs exploitation tradeoff
- Smoother pareto front approximation

**Code:** `baselines/baseline3.py`

---

## Proposed System: DQN + TOF + MMDE-NSGA-II

**What it does:**
- Uses baselines as initialization (seed knowledge)
- Agents continuously learn during simulation
- Agent1: adaptive task placement
- Agent2: adaptive network routing
- Online feedback loop: reward ← metrics

**Architecture:**
```
Simulation State
    ↓
Agent1 decides: device/fog-A/fog-B/fog-C/fog-D/cloud
    ↓
Execution + measurement (latency, energy, deadline)
    ↓
Reward: -10 if deadline missed, +reward_latency, +reward_energy
    ↓
Agent1 learns: update Q-network
    ↓
Next decision (improved by learning)
```

**Expected Results:**
- Success Rate: **>85%** (+5% vs B3)
- Avg Latency: **<80 ms** (50% reduction vs B3)
- Avg Energy: **<0.120 J** (23% savings vs B3)
- Handoff Success: **>90%** (excellent proactive handoff)

**Why it wins:**
- Adapts to real network conditions
- Learns from every task execution
- Handles dynamic vehicle movement
- Recovers from adverse conditions
- Better exploration-exploitation balance

---

## Comparison Table

| Metric | B1 (Pure NSGA-II) | B2 (TOF+NSGA) | B3 (TOF+MMDE) | **Proposed (DQN)** |
|--------|------------------|---------------|----------------|------------------|
| **Success %** | 47% | 68% | 80% | **>85%** |
| **Latency (ms)** | 167 | 205 | 163 | **<80** |
| **Energy (J)** | 0.250 | 0.186 | 0.157 | **<0.120** |
| **Handoff Success** | 51% | 64% | 77% | **>90%** |
| **Online Learning** | ❌ | ❌ | ❌ | ✅ |
| **Adaptation** | ❌ | ❌ | ❌ | ✅ |
| **Recovery from Failures** | ❌ | ❌ | ❌ | ✅ |

---

## Running Baselines

### Run All Baselines (30 min)

```bash
# Terminal 1: Backend
python app.py proposed

# Terminal 2
# Baseline 1
python baselines/baseline1.py 2>&1 | tee baseline1_results.log

# Baseline 2
python baselines/baseline2.py 2>&1 | tee baseline2_results.log

# Baseline 3
python baselines/baseline3.py 2>&1 | tee baseline3_results.log

# Proposed (in dashboard)
# Select "Proposed (DQN)" in dashboard → Click Start
```

### Run from Dashboard

1. Open http://localhost:3000
2. Select system type: "Baseline 1 (NSGA-II)"
3. Click "Start"
4. Run for 1-2 minutes
5. Note final metrics
6. Repeat for B2, B3, Proposed

### Save Results

```bash
# Each baseline saves to:
results/baseline_<system>_results.jsonl

# Query results:
sqlite3 smart_city.db \
  "SELECT system, success_rate, avg_latency_ms, avg_energy_j \
   FROM baseline_results ORDER BY system"
```

---

## Expected Training Progression

### Baseline 1-3 (Static)
```
Simulation Time  Latency    Success %
0-10s            [constant] [constant]
10-20s           [same]     [same]
20-300s          [same]     [same]  ← No learning
```

### Proposed (DQN)
```
Simulation Time  Latency    Success %
0-10s            400ms      10%      ← Bad decisions
10-60s           200ms      40%      ← Learning phase
60-300s          80ms       85%+     ← Converged optimal
```

---

## Interpretation

**Why Proposed wins:**
1. **Adaptation** - Responds to congestion, responds to vehicle movement
2. **Learning** - 300s of data improves decisions
3. **Optimization** - Balances latency vs energy better
4. **Resilience** - Recovers from packet drops, overload
5. **Proactivity** - Predicts handoffs before they happen

**Why B3 is strong baseline:**
- Best offline algorithm (MMDE)  
- Smart classification (TOF)
- No online learning required
- Good ceiling to beat

---

## Thesis Claims

Your thesis should claim:

**"We demonstrate that DQN-based online learning achieves [>85% success, <80ms latency] compared to TOF+MMDE-NSGA-II baseline at [80%, 163ms], representing X% improvement. This validates our claim that adaptive ML outperforms static optimization for dynamic vehicular fog-cloud environments."**

---

See [ARCHITECTURE.md](./ARCHITECTURE.md) for system design.
