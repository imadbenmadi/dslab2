# PCNME Experiments - Quick Start

## Setup

Run from the repository root (`c:\Users\ibenmadi\Desktop\dslab2`):

```bash
# Pre-training (generates DQN weights)
python pcnme/experiments/pretrain.py --batches 1000 --epochs 20 --log-level INFO

# Simulation (main experiment)
python pcnme/experiments/run_all.py --systems proposed greedy dqn_cold --log-level INFO

# Verification (sanity checks)
python pcnme/experiments/verify.py --input experiments/results/raw_results.csv

# Analysis (statistics and tables)
python pcnme/experiments/analyze.py --input experiments/results/raw_results.csv --output experiments/results/
```

## Data Generation

Real dataset generation is now available in `pcnme/utilities/data_gen.py`:

```python
from pcnme.utilities import RealisticDatasetGenerator

# Generate realistic mobility patterns
gen = RealisticDatasetGenerator(seed=42)
dataset = gen.generate_scenario('morning_rush', n_vehicles=50, duration_s=1800)

# Access traces and workload
traces = dataset['traces']  # vehicle trajectories
workload = dataset['workload']  # task arrivals
```

### Scenarios

- **morning_rush**: Urban mobility, heavy workload (2 tasks/min)
- **off_peak**: Mixed mobility, light workload (0.5 tasks/min)
- **evening_rush**: Urban mobility, heavy workload (2 tasks/min)

## Logging

All scripts save logs to `experiments/results/logs/` and `experiments/weights/logs/`:

```bash
# View recent logs
tail experiments/results/logs/*.log

# Search for issues
grep "ERROR\|WARNING\|FAIL" experiments/results/logs/*.log
```

## Utilities

Centralized code in `pcnme/utilities/`:

- **logging.py** - `setup_logging()` function (used by all scripts)
- **data_gen.py** - `MobilityGenerator`, `TaskWorkloadGenerator`, `RealisticDatasetGenerator`

No more duplicate code in experiment scripts.
