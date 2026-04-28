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