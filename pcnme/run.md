cd c:\Users\imed\Desktop\dslab2

# Step 1: Pre-training (5 min)
python experiments\pretrain.py --batches 1000 --epochs 20 --output experiments\weights\

# Step 2: Main simulations (3-5 hours)
python experiments\run_all.py --output experiments\results\raw_results.csv

# Step 3: Analysis
python experiments\analyze.py --input experiments\results\raw_results.csv

# Step 4: Visualizations
python experiments\make_charts.py --input experiments\results\ --output experiments\figures\

# Step 5: Verify
python experiments\verify.py --input experiments\results\raw_results.csv