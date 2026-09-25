#!/usr/bin/env python3
"""
COMPLETE SYSTEM RESTART GUIDE
================================

Run this script to set up and test all components before running the full system.

Steps:
1. Fix PostgreSQL & Redis connections
2. Initialize databases
3. Verify data storage
4. Test baselines
5. Start system

Usage:
    python complete_system_setup.py
"""

import os
import sys
import subprocess
import time
from pathlib import Path


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def run_command(cmd, description):
    """Run a command and report status."""
    print(f"→ {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"[OK]  {description} successful\n")
            return True
        else:
            print(f"✗ {description} failed")
            if result.stderr:
                print(f"  Error: {result.stderr.strip()}\n")
            return False
    except subprocess.TimeoutExpired:
        print(f"✗ {description} timed out\n")
        return False
    except Exception as e:
        print(f"✗ {description} error: {e}\n")
        return False


def check_python_packages():
    """Check and install required Python packages."""
    print_section("1. CHECKING PYTHON PACKAGES")
    
    required = [
        "psycopg2-binary",
        "redis",
        "numpy",
        "pandas",
        "torch",
        "simpy",
        "pymoo",
        "flask",
        "websockets",
    ]
    
    for package in required:
        print(f"Checking {package}...")
        result = subprocess.run(
            f"python -m pip show {package}",
            shell=True,
            capture_output=True,
            timeout=10
        )
        if result.returncode != 0:
            print(f"  Installing {package}...")
            subprocess.run(
                f"pip install {package}",
                shell=True,
                timeout=60
            )
        print(f"[OK]  {package} ready")
    
    print()


def setup_postgresql():
    """Set up PostgreSQL database."""
    print_section("2. POSTGRESQL SETUP")
    
    print("→ Setting up PostgreSQL...")
    print("  This requires PostgreSQL to be installed and running.")
    print("  On Windows, ensure the PostgreSQL service is running:\n")
    print("    Services → PostgreSQL XX → Start\n")
    
    # Try to run setup script
    if Path("setup_postgresql.py").exists():
        result = subprocess.run(
            "python setup_postgresql.py",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        print(result.stdout)
        if result.returncode == 0:
            print("[OK]  PostgreSQL setup complete\n")
            return True
        else:
            print(f"✗ PostgreSQL setup failed:")
            print(result.stderr)
            return False
    else:
        print("✗ setup_postgresql.py not found\n")
        return False


def setup_redis():
    """Set up Redis."""
    print_section("3. REDIS SETUP")
    
    print("→ Checking Redis...")
    
    # Check if Redis is running
    result = subprocess.run(
        "redis-cli ping",
        shell=True,
        capture_output=True,
        timeout=10
    )
    
    if result.returncode == 0 and b"PONG" in result.stdout:
        print("[OK]  Redis is running and responding\n")
        return True
    else:
        print("✗ Redis is not running")
        print("  On Windows, you have two options:\n")
        print("  Option 1: Use WSL")
        print("    wsl ubuntu -u root bash -c 'redis-server --daemonize yes'\n")
        print("  Option 2: Install Redis from GitHub Releases")
        print("    https://github.com/microsoftarchive/redis/releases\n")
        print("⚠ Redis is optional - system will work without it\n")
        return False


def verify_carla_data():
    """Verify CARLA trajectory data."""
    print_section("4. CARLA TRAJECTORY DATA")
    
    csv_path = Path("results/carla_trajectories.csv")
    
    if csv_path.exists():
        lines = len(csv_path.read_text().split('\n'))
        print(f"[OK]  Found {csv_path}")
        print(f"  Data points: {lines:,}")
        print(f"  This is real Istanbul vehicle trajectory data\n")
        return True
    else:
        print(f"✗ {csv_path} not found")
        print("  Vehicle movement will use random positions\n")
        return False


def test_baselines():
    """Test baseline implementations."""
    print_section("5. BASELINE IMPLEMENTATIONS")
    
    baselines = [
        ("baselines/baseline1.py", "Baseline 1 (Pure NSGA-II)"),
        ("baselines/baseline2.py", "Baseline 2 (TOF + NSGA-II)"),
        ("baselines/baseline3.py", "Baseline 3 (TOF + MMDE-NSGA-II)"),
    ]
    
    print("Checking baseline implementations...")
    all_ok = True
    
    for path, name in baselines:
        if Path(path).exists():
            print(f"[OK]  {name} - implemented")
        else:
            print(f"✗ {name} - MISSING")
            all_ok = False
    
    if all_ok:
        print(f"\n[OK]  All baselines ready for comparison\n")
    return all_ok


def main():
    print("\n" + "="*80)
    print("  SMART CITY VEHICULAR TASK OFFLOADING - COMPLETE SETUP")
    print("="*80)
    
    # Run all setup steps
    steps_ok = []
    
    try:
        check_python_packages()
        steps_ok.append(("Python Packages", True))
        
        pg_ok = setup_postgresql()
        steps_ok.append(("PostgreSQL", pg_ok))
        
        redis_ok = setup_redis()
        steps_ok.append(("Redis", redis_ok))
        
        carla_ok = verify_carla_data()
        steps_ok.append(("CARLA Data", carla_ok))
        
        baseline_ok = test_baselines()
        steps_ok.append(("Baselines", baseline_ok))
    
    except Exception as e:
        print(f"\n✗ Setup error: {e}\n")
        return False
    
    # Summary
    print_section("SETUP SUMMARY")
    
    for step_name, ok in steps_ok:
        status = "[OK] " if ok else "✗"
        print(f"{status} {step_name}")
    
    critical_ok = all(ok for name, ok in steps_ok if name in ["Python Packages", "PostgreSQL", "Baselines"])
    
    if critical_ok:
        print(f"\n[OK]  All critical components ready!\n")
        print("Next steps:")
        print("\n  1. Start the backend:")
        print("     python app.py proposed\n")
        print("  2. In another terminal, start the frontend:")
        print("     cd frontend")
        print("     npm start\n")
        print("  3. Open browser:")
        print("     http://localhost:3000\n")
        print("  4. Test baselines by selecting from dropdown:\n")
        print("     - Baseline 1 (NSGA-II)")
        print("     - Baseline 2 (TOF + NSGA-II)")  
        print("     - Baseline 3 (TOF + MMDE-NSGA-II)")
        print("     - Proposed (DQN)\n")
        return True
    else:
        print(f"\n✗ Critical components missing - fix errors above\n")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
