#!/usr/bin/env python
"""
PCNME Quick Start Guide
Interactive setup and first run.
"""

import sys
import subprocess
from pathlib import Path
import shutil


def print_banner():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║         PCNME - Proactive Computing for Network-Embedded         ║
║              Mobile Environments - Quick Start                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")


def check_dependencies():
    """Check if all required Python packages are installed."""
    print("\n[1/5] Checking dependencies...")

    required = [
        'torch', 'numpy', 'scipy', 'matplotlib', 'pandas', 'pymoo'
    ]

    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} (MISSING)")
            missing.append(package)

    if missing:
        print(f"\n⚠ Missing packages: {', '.join(missing)}")
        response = input("Install now? [y/n] ")
        if response.lower() == 'y':
            print("Installing dependencies...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r',
                          'requirements.txt'], check=True)
            print("✓ Dependencies installed")
        else:
            print("Cancelled. Please run: pip install -r requirements.txt")
            return False

    return True


def verify_structure():
    """Verify project structure is intact."""
    print("\n[2/5] Verifying project structure...")

    required_dirs = [
        'pcnme',
        'experiments',
        'experiments/data',
        'experiments/weights',
        'experiments/results',
    ]

    required_files = [
        'pcnme/__init__.py',
        'pcnme/constants.py',
        'pcnme/formulas.py',
        'experiments/pretrain.py',
        'experiments/run_all.py',
        'experiments/analyze.py',
        'requirements.txt',
        'README.md',
    ]

    all_ok = True
    for d in required_dirs:
        p = Path(d)
        if p.exists():
            print(f"  ✓ {d}/")
        else:
            print(f"  ✗ {d}/ (MISSING)")
            all_ok = False

    for f in required_files:
        p = Path(f)
        if p.exists():
            print(f"  ✓ {f}")
        else:
            print(f"  ✗ {f} (MISSING)")
            all_ok = False

    return all_ok


def run_demo():
    """Run a small demo simulation."""
    print("\n[3/5] Running demo simulation...")
    print("  This will run a single system, single scenario, single seed (~2 minutes)\n")

    response = input("Proceed with demo? [y/n] ")
    if response.lower() != 'y':
        print("Skipping demo.")
        return

    # Run a minimal simulation
    demo_code = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from pcnme import (
    TaskRecord, MetricsCollector, DataManager,
    SimulationEnvironment, create_system, SEEDS
)

print("Generating mobility traces...")
data_manager = DataManager()
traces = data_manager.get_traces('off_peak', n_vehicles=10, seed=42)

print(f"Initializing simulation environment...")
env = SimulationEnvironment(seed=42)
env.initialize(traces)

print(f"Creating greedy system (baseline)...")
system = create_system('greedy', env, seed=42)

print(f"Running simulation...")
metrics = MetricsCollector()
task_id = 0

while env.sim_time_s < 60.0:  # Just 60 seconds for demo
    for vehicle_id in env.vehicles:
        if int(env.sim_time_s) % 10 == 0:
            # Simplified task execution
            fog_state = env.get_fog_state()
            dest = system.select_destination(2, vehicle_id, fog_state)
            
            task_id += 1
            if int(env.sim_time_s) % 60 == 0:
                print(f"  {env.sim_time_s:.0f}s: Task {task_id} -> {dest}")
    
    env.step()

print(f"✓ Demo complete: {task_id} tasks executed in 60 seconds")
"""

    result = subprocess.run([sys.executable, '-c', demo_code], 
                          capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Warnings:", result.stderr)

    if result.returncode == 0:
        print("  ✓ Demo successful!")
    else:
        print("  ✗ Demo failed")


def show_next_steps():
    """Show next steps for full simulation."""
    print("\n[4/5] Next steps for full simulation:")
    print("""
1. PRE-TRAINING (one-time, ~5 minutes):
   cd experiments
   python pretrain.py --batches 1000 --output weights/ --epochs 20

2. MAIN SIMULATIONS (90 runs, ~3-5 hours):
   python run_all.py --output results/raw_results.csv --weights weights/

3. ANALYSIS:
   python analyze.py --input results/raw_results.csv --output results/

4. VISUALIZATION:
   python make_charts.py --input results/ --output figures/ --dpi 300

5. VERIFICATION:
   python verify.py --input results/raw_results.csv
""")


def show_resources():
    """Show available resources."""
    print("\n[5/5] Available resources:")
    print("""
📖 Documentation:
   - README.md (comprehensive usage guide)
   - IMPLEMENTATION_SUMMARY.md (complete feature list)
   - Source code is well-documented

📊 Example Commands:
   # Run only proposed system + greedy for testing:
   python run_all.py --systems proposed greedy --n-vehicles 10

   # Generate figures only (requires raw_results.csv):
   python make_charts.py --input results/ --output figures/

   # Full statistical analysis:
   python analyze.py --input results/raw_results.csv --output results/

🔧 Configuration:
   - Edit pcnme/constants.py to change system parameters
   - All systems automatically use updated constants

📁 Project Structure:
   pcnme/          - Main package (10 modules)
   experiments/    - Execution scripts (5 scripts)
   README.md       - Comprehensive guide
""")


def main():
    print_banner()

    # Check dependencies
    if not check_dependencies():
        print("\n❌ Cannot proceed without dependencies")
        return 1

    # Verify structure
    if not verify_structure():
        print("\n⚠ Project structure incomplete")

    # Run demo
    run_demo()

    # Show next steps
    show_next_steps()

    # Show resources
    show_resources()

    print("\n╔══════════════════════════════════════════════╗")
    print("║  ✓ Quick Start Complete!                    ║")
    print("║  Ready for full simulations                 ║")
    print("║  See details above for next steps            ║")
    print("╚══════════════════════════════════════════════╝\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
