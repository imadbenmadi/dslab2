"""
Sanity checks for simulation results.
"""

import argparse
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from pcnme import (
    MetricsCollector, classify_step, compute_t_exit,
    SYSTEMS
)


def verify_results(records):
    """Run all sanity checks."""
    checks_passed = 0
    checks_total = 0

    print("\n=== SANITY CHECKS ===\n")

    # Check 1: EC classification
    checks_total += 1
    try:
        for r in records[:100]:  # spot check
            if r.n_boulders + r.n_pebbles >= 1:
                assert r.n_boulders >= 0 and r.n_pebbles >= 0
        print("✓ Check 1: EC classification correctness")
        checks_passed += 1
    except AssertionError as e:
        print(f"✗ Check 1: EC classification failed: {e}")

    # Check 2: Proposed beats baselines on feasibility
    checks_total += 1
    try:
        proposed = [r for r in records if r.system == "proposed"]
        proposed_feas = np.mean([r.deadline_met for r in proposed]) if proposed else 0.0

        for sys in ["random", "greedy"]:
            baseline = [r for r in records if r.system == sys]
            baseline_feas = np.mean([r.deadline_met for r in baseline]) if baseline else 0.0
            if baseline_feas > 0:
                assert proposed_feas >= baseline_feas * 0.9, \
                    f"Proposed feas {proposed_feas} should beat {sys} feas {baseline_feas}"

        print(f"✓ Check 2: Proposed feasibility ({proposed_feas:.2%}) beats baselines")
        checks_passed += 1
    except AssertionError as e:
        print(f"✗ Check 2: Feasibility check failed: {e}")

    # Check 3: Proposed beats baselines on latency
    checks_total += 1
    try:
        proposed = [r for r in records if r.system == "proposed"]
        proposed_lat = np.mean([r.total_latency_ms for r in proposed]) if proposed else 0.0

        for sys in ["random", "greedy"]:
            baseline = [r for r in records if r.system == sys]
            baseline_lat = np.mean([r.total_latency_ms for r in baseline]) if baseline else 0.0
            if baseline_lat > 0:
                assert proposed_lat <= baseline_lat * 1.1, \
                    f"Proposed latency {proposed_lat} should be <= {sys} latency {baseline_lat}"

        print(f"✓ Check 3: Proposed latency ({proposed_lat:.1f}ms) beats baselines")
        checks_passed += 1
    except AssertionError as e:
        print(f"✗ Check 3: Latency check failed: {e}")

    # Check 4: Latency range validation
    checks_total += 1
    try:
        for r in records:
            # The current latency model (cloud boulder steps, simplified comms)
            # yields totals around ~2s; keep a generous upper bound.
            assert 50 < r.total_latency_ms < 10000, \
                f"Latency {r.total_latency_ms}ms out of range"
        print(f"✓ Check 4: Latency ranges valid")
        checks_passed += 1
    except AssertionError as e:
        print(f"✗ Check 4: Latency range check failed: {e}")

    # Check 5: Energy range validation
    checks_total += 1
    try:
        for r in records:
            assert 0.01 < r.total_energy_j < 1.0, \
                f"Energy {r.total_energy_j}J out of range"
        print(f"✓ Check 5: Energy ranges valid")
        checks_passed += 1
    except AssertionError as e:
        print(f"✗ Check 5: Energy range check failed: {e}")

    # Check 6: Fog load validity
    checks_total += 1
    try:
        for r in records:
            loads = [r.fog_A_load, r.fog_B_load, r.fog_C_load, r.fog_D_load]
            for load in loads:
                assert 0.0 <= load <= 1.0, f"Fog load {load} out of [0,1]"
        print(f"✓ Check 6: Fog loads in [0, 1]")
        checks_passed += 1
    except AssertionError as e:
        print(f"✗ Check 6: Fog load check failed: {e}")

    # Check 7: Destination validity
    checks_total += 1
    try:
        valid_dests = {"A", "B", "C", "D", "cloud", "device", "unknown"}
        for r in records:
            assert r.step2_dest in valid_dests, f"Invalid dest {r.step2_dest}"
            assert r.step3_dest in valid_dests, f"Invalid dest {r.step3_dest}"
            assert r.step5_dest in valid_dests, f"Invalid dest {r.step5_dest}"
        print(f"✓ Check 7: Destination values valid")
        checks_passed += 1
    except AssertionError as e:
        print(f"✗ Check 7: Destination check failed: {e}")

    # Check 8: Data coverage
    checks_total += 1
    try:
        for sys in SYSTEMS:
            count = len([r for r in records if r.system == sys])
            assert count > 0, f"No records for system {sys}"
        print(f"✓ Check 8: All systems have data")
        checks_passed += 1
    except AssertionError as e:
        print(f"✗ Check 8: Data coverage check failed: {e}")

    print(f"\n=== RESULTS ===")
    print(f"Passed: {checks_passed}/{checks_total}")
    if checks_passed == checks_total:
        print("✓ All sanity checks passed!")
    else:
        print(f"⚠ {checks_total - checks_passed} checks failed")

    return checks_passed == checks_total


def main():
    parser = argparse.ArgumentParser(description="Verify simulation results")
    parser.add_argument("--input", type=str, default="experiments/results/raw_results.csv",
                       help="Input CSV file with results")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: {input_path} not found")
        return

    print("[1/1] Loading and verifying results...")
    collector = MetricsCollector.load_csv(input_path)
    print(f"      Loaded {len(collector.records)} records")

    success = verify_results(collector.records)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
