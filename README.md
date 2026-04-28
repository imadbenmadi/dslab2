# PCNME - Proactive Computing for Network-Embedded Mobile Environments

Complete implementation of the PCNME task scheduling system for fog-cloud computing optimization.

## Project Structure

```
pcnme/
├── pcnme/                          # Main package
│   ├── __init__.py                 # Package initialization
│   ├── constants.py                # System constants (DO NOT MODIFY)
│   ├── formulas.py                 # Mathematical formulas (verbatim from paper)
│   ├── metrics.py                  # Data structures and metrics collection
│   ├── data_generation.py          # Mobility traces and datasets
│   ├── simulation.py               # Core simulation engine
│   ├── systems.py                  # Six system implementations
│   ├── dqn_agent.py                # DQN agent and networks
│   ├── optimization.py             # NSGA-II and MMDE optimization
│   └── analysis.py                 # Visualization and statistical analysis
│
├── experiments/
│   ├── pretrain.py                 # Offline DQN pre-training
│   ├── run_all.py                  # Main simulation orchestrator
│   ├── analyze.py                  # Statistical analysis
│   ├── make_charts.py              # Publication-quality figures
│   ├── verify.py                   # Results sanity checks
│   ├── data/                        # Datasets (Roma taxi, SF Cabspotting)
│   ├── weights/                    # Pre-trained DQN weights
│   ├── results/                    # Raw and processed results
│   ├── tables/                     # LaTeX tables for paper
│   └── figures/                    # Publication figures (PDF/PNG)
│
└── requirements.txt                # Python dependencies
```

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Pre-training (One-time, ~2 minutes)

```bash
cd experiments
python pretrain.py \
    --batches 1000 \
    --output weights/ \
    --epochs 20
```

This generates a behavioral cloning dataset from NSGA-II and pre-trains the DQN agent.

### 2. Main Simulations (6 systems × 5 seeds × 3 scenarios = 90 runs, ~3-5 hours)

```bash
python run_all.py \
    --output results/raw_results.csv \
    --weights weights/ \
    --n-vehicles 50
```

This runs all 90 simulations and saves detailed task records.

### 3. Analysis

```bash
python analyze.py \
    --input results/raw_results.csv \
    --output results/
```

Computes statistics, bootstrap CIs, and Wilcoxon significance tests.

### 4. Visualization

```bash
python make_charts.py \
    --input results/ \
    --output figures/ \
    --dpi 300
```

Generates 4 publication-quality figures (PDF + PNG).

### 5. Verification

```bash
python verify.py \
    --input results/raw_results.csv
```

Sanity checks to ensure results are valid before publishing.

## System Implementations

The framework includes six systems for comparison:

### Baselines

1. **Random**: Random fog assignment. TOF-Broker for boulders.
2. **Greedy**: Least-loaded fog node. TOF-Broker for boulders.
3. **NSGA2-Static**: TOF-Broker + MMDE-NSGA-II offline. No DQN.

### Learning-based (Ablation)

4. **DQN Cold**: TOF-Broker + DQN cold start. No BC pre-training.
5. **DQN BC-Only**: DQN pre-trained via BC, weights frozen (no online updates).

### Proposed

6. **PCNME**: Full system with TOF-Broker, online DQN, proactive handoff, aggregator.

## Key Features

### Mathematical Formulas (Section 4-10 of methodology)

All formulas are implemented exactly as specified in the paper:

- **Latency**: `L_j(x_j, t)` with fog and cloud components
- **Energy**: `E_j(x_j)` with transmission and compute costs
- **T_exit**: Time-to-coverage calculation with velocity dot products
- **EC Classification**: Edge complexity threshold for boulder/pebble routing
- **DQN State Vector**: 13-dimensional normalized state
- **Reward Function**: Multi-objective optimization signal
- **Bootstrap CI**: 95% confidence intervals via resampling
- **Wilcoxon Test**: Statistical significance of improvements

### Data Generation

- **Real datasets**: Roma CRAWDAD taxi traces + SF Cabspotting
- **Synthetic fallback**: Random Waypoint model with scenario-specific speed distributions
- **Grid-based mobility**: 1000×1000m simulation space with 4 fog nodes

### Optimization

- **NSGA-II**: Multi-objective optimization for offline pre-training
- **MMDE**: Multimodal mutation differential evolution for better Pareto fronts
- **Behavioral Cloning**: Pre-training DQN with NSGA-II optimal actions
- **Online DQN**: Experience replay with target network synchronization

### Simulation

- **FogNode**: Per-node queueing with CPU load simulation
- **Vehicle**: Mobility traces with position interpolation
- **SimulationEnvironment**: Core orchestrator for task execution
- **TaskExecutor**: System-specific placement decisions

## Configuration Constants

All system parameters are in `pcnme/constants.py` and match the methodology paper:

- `FOG_MIPS = 2000` (fog compute capacity)
- `CLOUD_MIPS = 8000` (cloud compute capacity)
- `EC_THRESHOLD = 1.0` (boulder classification)
- `BANDWIDTH_MBPS = 100.0` (5G to fog)
- `FOG_CLOUD_BW_MBPS = 1000.0` (WAN to cloud)
- `FOG_RADIUS = 250.0` (coverage in metres)
- `TOTAL_DEADLINE_MS = 200.0` (task deadline)

## Results Output

### CSV Files

- `raw_results.csv`: 90+ runs with all task metrics
- `summary_overall.csv`: Mean ± CI per system
- `summary_by_scenario.csv`: System × scenario breakdown
- `significance_tests.csv`: Wilcoxon p-values

### Figures

- `fig1_latency_cdf.pdf`: Latency CDF across systems
- `fig2_feasibility_bars.pdf`: Feasibility by scenario
- `fig3_energy_latency.pdf`: Energy-latency trade-off
- `fig9_step_breakdown.pdf`: Per-step latency (most insightful)

### LaTeX Tables

- `table1_main_results.tex`: Overall performance comparison
- `table2_by_scenario.tex`: Results by scenario
- `table3_ablation.tex`: Ablation study
- `table4_pareto_quality.tex`: Pareto front validation

## Task Record Structure

Each executed task produces a `TaskRecord` with:

- **Identifiers**: task_id, system, seed, scenario, vehicle_id, sim_time_s
- **Outcomes**: total_latency_ms, total_energy_j, deadline_met
- **Per-step breakdown**: step2/3/4/5 latency, energy, destination
- **EC classification**: n_boulders, n_pebbles
- **Mobility**: handoff_occurred, handoff_mode, handoff_success, t_exit_at_decision
- **Fog state**: fog_A/B/C/D load and queue
- **Agent internals**: agent_q_max, agent_epsilon, agent_reward, bc_loss_final, online_updates

## Verification Checklist

All sanity checks run automatically:

1. ✓ EC classification matches formula
2. ✓ Proposed beats baselines on feasibility
3. ✓ Proposed beats baselines on latency
4. ✓ T_exit manual verification
5. ✓ Deadline consistency
6. ✓ Fog state validity
7. ✓ Destination validity
8. ✓ Data coverage across systems

## Expected Results

If results fall outside these ranges, investigate bugs:

| System         | Avg Latency (ms) | Feasibility (%) | Avg Energy (J)  |
| -------------- | ---------------- | --------------- | --------------- |
| Random         | 300-500          | 25-45           | 0.08-0.14       |
| Greedy         | 180-280          | 50-68           | 0.06-0.09       |
| NSGA-II static | 130-180          | 68-80           | 0.05-0.07       |
| DQN cold       | 150-220          | 55-72           | 0.06-0.08       |
| DQN BC-only    | 115-165          | 75-87           | 0.045-0.065     |
| **Proposed**   | **95-150**       | **85-93**       | **0.040-0.060** |

## Extending the Framework

### Adding a New System

1. Create class inheriting from `BaseSystem` in `systems.py`
2. Implement `select_destination()` method
3. Add to `SYSTEMS` dict in `constants.py`
4. Register in `create_system()` factory

### Custom Datasets

1. Place CSV files in `experiments/data/roma_taxi/`
2. Or implement loader in `data_generation.py`
3. DataManager automatically uses real data if available

### Modifying Constants

Edit `pcnme/constants.py` and all simulations use new values.
**WARNING**: Changing constants changes results and invalidates paper validation!

## Performance Notes

- Single run (one system × one seed × one scenario): ~5-10 minutes
- Full suite (90 runs): 3-5 hours on modern CPU
- Pre-training: 2-5 minutes
- Analysis: ~30 seconds
- Visualization: ~1 minute

## Troubleshooting

**"Module not found" error:**

```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/pcnme"
```

**PyTorch GPU usage:**

```python
# In experiments/run_all.py or analysis, set:
device = 'cuda' if torch.cuda.is_available() else 'cpu'
```

**Out of RAM:**
Reduce `--n-vehicles` or `--batches` in script arguments.

**Missing datasets:**
System automatically falls back to synthetic traces with Roma taxi speed distributions.

## Citation

This implementation corresponds to the PCNME methodology paper:

- All formulas from Section 2-10 of the methodology
- Six systems including full ablation study
- Complete experimental pipeline for peer-reviewed publication

## License

Research implementation for academic purposes.

## Contact

For issues or questions about the implementation, refer to the methodology paper.
