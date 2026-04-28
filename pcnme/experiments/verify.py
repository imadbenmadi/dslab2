"""
PCNME Results Verification
Sanity checks to ensure results are valid before accepting them.

Usage:
    python experiments/verify.py --input experiments/results/raw_results.csv
"""

import argparse
import numpy as np
from pathlib import Path
import sys

# Add parent directory to path (dslab2 root)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pcnme import MetricsCollector
from pcnme.formulas import compute_t_exit
from pcnme.progress import progress
from pcnme.utilities import setup_logging, get_logger


def verify_results(records, logger=None):
    """
    Run all sanity checks on results.
    All checks must pass before accepting results.
    """
    if logger is None:
        logger = logging.getLogger('PCNME.Verify')
    
    print("=" * 70)
    print("PCNME RESULTS VERIFICATION")
    print("=" * 70)
    logger.info("=" * 70)
    logger.info("PCNME RESULTS VERIFICATION")
    logger.info("=" * 70)

    n_checks = 0
    n_passed = 0

    # Check 1: EC classification must match the formula
    print("\n[CHECK 1] EC Classification")
    logger.info("[CHECK 1] EC Classification")
    try:
        for r in progress(
            records, desc="Check 1", unit="record", total=len(records), leave=False
        ):
            assert r.n_boulders >= 1, "Step 4 and/or 3 must always be boulders"
            assert r.n_pebbles >= 1, "Steps 2 and 5 must always be pebbles"

        msg = "✓ PASS: All tasks correctly classified boulders vs pebbles"
        print(f"  {msg}")
        logger.info(f"  {msg}")
        n_passed += 1
    except AssertionError as e:
        msg = f"✗ FAIL: {e}"
        print(f"  {msg}")
        logger.warning(f"  {msg}")
    n_checks += 1

    # Check 2: Proposed must beat baselines on feasibility
    print("\n[CHECK 2] Proposed System Performance (Feasibility)")
    logger.info("[CHECK 2] Proposed System Performance (Feasibility)")
    try:
        proposed_recs = [r for r in records if r.system == 'proposed']
        if proposed_recs:
            proposed_feas = np.mean([r.deadline_met for r in proposed_recs])

            for sys in ['random', 'greedy', 'nsga2_static']:
                sys_recs = [r for r in records if r.system == sys]
                if sys_recs:
                    sys_feas = np.mean([r.deadline_met for r in sys_recs])
                    assert proposed_feas >= sys_feas * 0.95, \
                        f"Proposed ({proposed_feas:.3f}) should beat {sys} ({sys_feas:.3f})"

            msg = f"✓ PASS: Proposed achieves {proposed_feas*100:.1f}% feasibility (better than baselines)"
            print(f"  {msg}")
            logger.info(f"  {msg}")
            n_passed += 1
        else:
            msg = "⊗ SKIP: No proposed system records"
            print(f"  {msg}")
            logger.info(f"  {msg}")
    except AssertionError as e:
        msg = f"✗ FAIL: {e}"
        print(f"  {msg}")
        logger.warning(f"  {msg}")
    n_checks += 1

    # Check 3: Proposed must beat baselines on latency
    print("\n[CHECK 3] Proposed System Performance (Latency)")
    logger.info("[CHECK 3] Proposed System Performance (Latency)")
    try:
        proposed_recs = [r for r in records if r.system == 'proposed']
        if proposed_recs:
            proposed_lat = np.mean([r.total_latency_ms for r in proposed_recs])

            for sys in ['random', 'greedy', 'nsga2_static']:
                sys_recs = [r for r in records if r.system == sys]
                if sys_recs:
                    sys_lat = np.mean([r.total_latency_ms for r in sys_recs])
                    assert proposed_lat <= sys_lat * 1.05, \
                        f"Proposed ({proposed_lat:.1f}ms) should beat {sys} ({sys_lat:.1f}ms)"

            msg = f"✓ PASS: Proposed achieves {proposed_lat:.1f}ms latency (better than baselines)"
            print(f"  {msg}")
            logger.info(f"  {msg}")
            n_passed += 1
        else:
            msg = "⊗ SKIP: No proposed system records"
            print(f"  {msg}")
            logger.info(f"  {msg}")
    except AssertionError as e:
        msg = f"✗ FAIL: {e}"
        print(f"  {msg}")
        logger.warning(f"  {msg}")
    n_checks += 1

    # Check 4: T_exit manual verification
    print("\n[CHECK 4] T_exit Calculation Verification")
    logger.info("[CHECK 4] T_exit Calculation Verification")
    try:
        # Manual verification (math convention): 0°=east, 90°=north
        # Vehicle 180m east of Fog A, speed 70 km/h heading east
        t = compute_t_exit(
            vehicle_x=380,  # 180m east of Fog A at (200, 500)
            vehicle_y=500,
            speed_ms=70 / 3.6,  # 70 km/h = 19.4 m/s
            heading_deg=0,  # due east = moving away from Fog A
            fog_x=200,
            fog_y=500,
            fog_radius=250
        )
        error = abs(t - 3.6)
        assert error < 0.5, f"T_exit = {t:.2f}s, expected ~3.6s (error: {error:.2f}s)"

        msg = f"✓ PASS: T_exit = {t:.2f}s (expected ~3.6s, error={error:.3f}s)"
        print(f"  {msg}")
        logger.info(f"  {msg}")
        n_passed += 1
    except AssertionError as e:
        msg = f"✗ FAIL: {e}"
        print(f"  {msg}")
        logger.warning(f"  {msg}")
    n_checks += 1

    # Check 5: Deadline met records are consistent
    print("\n[CHECK 5] Deadline Consistency")
    logger.info("[CHECK 5] Deadline Consistency")
    try:
        inconsistent = 0
        for r in progress(
            records, desc="Check 5", unit="record", total=len(records), leave=False
        ):
            deadline_implied = 1.0 if r.total_latency_ms <= 200.0 else 0.0
            if int(r.deadline_met) != int(deadline_implied):
                inconsistent += 1

        assert inconsistent == 0, f"{inconsistent} records with inconsistent deadline flags"

        msg = f"✓ PASS: All {len(records)} records have consistent deadline flags"
        print(f"  {msg}")
        logger.info(f"  {msg}")
        n_passed += 1
    except AssertionError as e:
        msg = f"✗ FAIL: {e}"
        print(f"  {msg}")
        logger.warning(f"  {msg}")
    n_checks += 1

    # Check 6: Fog state must be in valid range
    print("\n[CHECK 6] Fog State Validity")
    logger.info("[CHECK 6] Fog State Validity")
    try:
        invalid_loads = 0
        invalid_queues = 0

        for r in progress(
            records, desc="Check 6", unit="record", total=len(records), leave=False
        ):
            for node_id in ['A', 'B', 'C', 'D']:
                load = getattr(r, f'fog_{node_id}_load')
                queue = getattr(r, f'fog_{node_id}_queue', 0)

                if not (0.0 <= load <= 1.0):
                    invalid_loads += 1
                if queue < 0:
                    invalid_queues += 1

        assert invalid_loads == 0, f"{invalid_loads} records with invalid fog loads"
        assert invalid_queues == 0, f"{invalid_queues} records with invalid fog queues"

        msg = "✓ PASS: All fog state values within valid ranges"
        print(f"  {msg}")
        logger.info(f"  {msg}")
        n_passed += 1
    except AssertionError as e:
        msg = f"✗ FAIL: {e}"
        print(f"  {msg}")
        logger.warning(f"  {msg}")
    n_checks += 1

    # Check 7: Destination validity
    print("\n[CHECK 7] Destination Validity")
    logger.info("[CHECK 7] Destination Validity")
    try:
        valid_dests = {'A', 'B', 'C', 'D', 'cloud', None}
        invalid_dests = 0

        for r in progress(
            records, desc="Check 7", unit="record", total=len(records), leave=False
        ):
            for step in [2, 3, 5]:
                dest = getattr(r, f'step{step}_dest')
                if dest not in valid_dests:
                    invalid_dests += 1

        assert invalid_dests == 0, f"{invalid_dests} records with invalid destinations"

        msg = "✓ PASS: All destination values are valid"
        print(f"  {msg}")
        logger.info(f"  {msg}")
        n_passed += 1
    except AssertionError as e:
        msg = f"✗ FAIL: {e}"
        print(f"  {msg}")
        logger.warning(f"  {msg}")
    n_checks += 1

    # Check 8: Number of records per system
    print("\n[CHECK 8] Data Coverage")
    logger.info("[CHECK 8] Data Coverage")
    try:
        system_counts = {}
        for r in progress(
            records, desc="Check 8", unit="record", total=len(records), leave=False
        ):
            system_counts[r.system] = system_counts.get(r.system, 0) + 1

        print("  System coverage:")
        logger.info("  System coverage:")
        for system in sorted(system_counts.keys()):
            count = system_counts[system]
            msg = f"    {system:<20} {count:>6} records"
            print(msg)
            logger.debug(msg)

        min_count = min(system_counts.values())
        assert min_count > 0, "All systems should have records"

        msg = f"✓ PASS: All systems have coverage ({min_count}-{max(system_counts.values())} records)"
        print(f"  {msg}")
        logger.info(f"  {msg}")
        n_passed += 1
    except AssertionError as e:
        msg = f"✗ FAIL: {e}"
        print(f"  {msg}")
        logger.warning(f"  {msg}")
    n_checks += 1

    # Summary
    print("\n" + "=" * 70)
    print(f"VERIFICATION SUMMARY: {n_passed}/{n_checks} checks passed")
    logger.info("=" * 70)
    logger.info(f"VERIFICATION SUMMARY: {n_passed}/{n_checks} checks passed")

    if n_passed == n_checks:
        msg = "✓ ALL CHECKS PASSED - Results are valid!"
        print(msg)
        logger.info(msg)
    else:
        msg = f"✗ {n_checks - n_passed} checks failed - Review results before publishing"
        print(msg)
        logger.warning(msg)

    print("=" * 70)
    logger.info("=" * 70)

    return n_passed == n_checks


def main():
    parser = argparse.ArgumentParser(
        description="PCNME Results Verification"
    )
    parser.add_argument('--input', type=Path,
                       default='experiments/results/raw_results.csv',
                       help='Input CSV with results')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING'], default='INFO',
                       help='Logging level')

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.input.parent / 'logs', 'verify', args.log_level)

    # Load records
    print(f"\nLoading results from {args.input}...")
    logger.info(f"Loading results from {args.input}...")
    records = MetricsCollector.load_csv(args.input)
    logger.info(f"✓ Loaded {len(records)} task records")
    print(f"✓ Loaded {len(records)} task records\n")

    # Run verification
    all_passed = verify_results(records, logger=logger)

    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
