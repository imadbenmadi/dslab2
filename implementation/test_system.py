#!/usr/bin/env python3
"""
Quick System Verification Test
Checks all components are working
"""
import sys
import os

print("=" * 80)
print("SMART CITY SYSTEM - QUICK TEST")
print("=" * 80)
print()

# 1. Check Python packages
print("1. CHECKING DEPENDENCIES")
print("-" * 80)

packages = {
    'flask': 'Flask REST API',
    'torch': 'PyTorch DQN',
    'psycopg2': 'PostgreSQL driver',
    'redis': 'Redis client',
    'pymoo': 'Multi-objective optimization',
    'numpy': 'Numerical computing',
    'pandas': 'Data processing',
    'simpy': 'Discrete event simulator',
}

installed = 0
for pkg, desc in packages.items():
    try:
        __import__(pkg)
        print(f"  [OK]  {pkg:<15} {desc}")
        installed += 1
    except ImportError:
        print(f"  ✗ {pkg:<15} {desc}")

print(f"\nResult: {installed}/{len(packages)} packages installed")
print()

# 2. Check project structure
print("2. CHECKING PROJECT STRUCTURE")
print("-" * 80)

dirs = [
    'agents', 'baselines', 'broker', 'environment', 'mobility',
    'optimizer', 'results', 'sdn', 'simulation', 'storage',
    'visualization', 'frontend', 'docs'
]

found = 0
for d in dirs:
    path = os.path.join(os.getcwd(), d)
    if os.path.isdir(path):
        print(f"  [OK]  {d}/")
        found += 1
    else:
        print(f"  ✗ {d}/")

print(f"\nResult: {found}/{len(dirs)} directories found")
print()

# 3. Check core files
print("3. CHECKING CORE FILES")
print("-" * 80)

files = {
    'app.py': 'Main orchestrator',
    'config.py': 'Configuration',
    'setup_postgresql.py': 'Database setup',
    'complete_system_setup.py': 'System verification',
    'requirements.txt': 'Dependencies',
    'README.md': 'Documentation',
}

found = 0
for fname, desc in files.items():
    path = os.path.join(os.getcwd(), fname)
    if os.path.isfile(path):
        size = os.path.getsize(path)
        print(f"  [OK]  {fname:<30} ({size:,} bytes) - {desc}")
        found += 1
    else:
        print(f"  ✗ {fname:<30} - {desc}")

print(f"\nResult: {found}/{len(files)} core files found")
print()

# 4. Check baseline implementations
print("4. CHECKING BASELINE IMPLEMENTATIONS")
print("-" * 80)

baselines = {
    'baselines/baseline1.py': 'Pure NSGA-II (400+ lines)',
    'baselines/baseline2.py': 'TOF + NSGA-II (450+ lines)',
    'baselines/baseline3.py': 'TOF + MMDE-NSGA-II (480+ lines)',
}

found = 0
for fname, desc in baselines.items():
    path = os.path.join(os.getcwd(), fname)
    if os.path.isfile(path):
        lines = len(open(path).readlines())
        print(f"  [OK]  {fname:<30} ({lines:>4} lines) - {desc}")
        found += 1
    else:
        print(f"  ✗ {fname:<30} - {desc}")

print(f"\nResult: {found}/{len(baselines)} baselines implemented")
print()

# 5. Check documentation
print("5. CHECKING DOCUMENTATION")
print("-" * 80)

docs = {
    'docs/INDEX.md': 'Navigation hub',
    'docs/architecture/ARCHITECTURE.md': 'System design',
    'docs/architecture/BASELINES.md': 'Baseline explanations',
    'docs/guides/QUICKSTART.md': 'Getting started',
    'docs/deployment/SETUP.md': 'Installation guide',
    'docs/deployment/DATABASE.md': 'Database configuration',
}

found = 0
for fname, desc in docs.items():
    path = os.path.join(os.getcwd(), fname)
    if os.path.isfile(path):
        lines = len(open(path).readlines())
        print(f"  [OK]  {fname:<40} ({lines:>3} lines)")
        found += 1
    else:
        print(f"  ✗ {fname:<40}")

print(f"\nResult: {found}/{len(docs)} documentation files created")
print()

# 6. Summary
print("=" * 80)
print("SYSTEM SUMMARY")
print("=" * 80)

total_checks = installed + found + len(dirs) + len(files) + len(baselines) + len(docs)
max_checks = len(packages) + len(dirs) + len(files) + len(baselines) + len(docs)

print(f"  Dependencies:    {installed}/{len(packages)} installed")
print(f"  Directories:     {found}/{len(dirs)} found")
print(f"  Core files:      {found}/{len(files)} found")
print(f"  Baselines:       {found}/{len(baselines)} implemented")
print(f"  Documentation:   {found}/{len(docs)} created")
print()

# 7. Next steps
print("=" * 80)
print("NEXT STEPS")
print("=" * 80)
print()
print("1. Start backend:")
print("   python app.py proposed")
print()
print("2. In another terminal, start frontend:")
print("   cd frontend && npm start")
print()
print("3. Open browser:")
print("   http://localhost:3000")
print()
print("4. Click 'Start' button to begin simulation")
print()
print("For documentation, see: docs/INDEX.md")
print()
print("=" * 80)
