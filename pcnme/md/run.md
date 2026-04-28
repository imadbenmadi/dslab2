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