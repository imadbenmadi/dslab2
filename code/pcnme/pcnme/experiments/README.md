# PCNME Experiments - Quick Start

## Setup

Run from the repository root (`c:\Users\ibenmadi\Desktop\dslab2`):

```bash
# 1. Pre-training (Generates 2,000 rows of real math & trains DQN)
python pcnme/experiments/pretrain.py --batches 20 --epochs 20 --log-level INFO

# 2. Simulation (Main experiment - runs all 6 systems)
python pcnme/experiments/run_all.py --log-level INFO

# 3. Verification (Sanity checks the results)
python pcnme/experiments/verify.py --input pcnme/experiments/results/raw_results.csv

# 4. Analysis (Generates statistics and summary tables)
python pcnme/experiments/analyze.py --input pcnme/experiments/results/raw_results.csv --output pcnme/experiments/results/

# 5. Visualization (Generates the 4 PDF/PNG charts for the paper)
python pcnme/experiments/make_charts.py --input pcnme/experiments/results/ --output pcnme/experiments/figures/
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
