"""
PCNME Results Analysis
Performs statistical analysis and generates summary tables.

Usage:
    python experiments/analyze.py \\
        --input experiments/results/raw_results.csv \\
        --output experiments/results/
"""

import argparse
import numpy as np
from pathlib import Path
import csv
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from pcnme import TaskRecord, MetricsCollector, ResultsAnalyzer
from pcnme.analysis import ResultsAnalyzer


def main():
    parser = argparse.ArgumentParser(
        description="PCNME Results Analysis"
    )
    parser.add_argument('--input', type=Path,
                       default='experiments/results/raw_results.csv',
                       help='Input CSV with raw results')
    parser.add_argument('--output', type=Path,
                       default='experiments/results/',
                       help='Output directory')

    args = parser.parse_args()

    print("=" * 70)
    print("PCNME RESULTS ANALYSIS")
    print("=" * 70)

    # Load records
    print(f"\nLoading results from {args.input}...")
    records = MetricsCollector.load_csv(args.input)
    print(f"✓ Loaded {len(records)} task records")

    # Create analyzer
    analyzer = ResultsAnalyzer(records)

    # Generate summary table
    print("\n" + "=" * 120)
    analyzer.generate_summary_table()

    # Statistical significance tests
    analyzer.compute_significance_tests()

    # Save summary statistics
    args.output.mkdir(parents=True, exist_ok=True)

    metrics = analyzer.compute_system_metrics()
    summary_path = args.output / 'summary_overall.csv'

    with open(summary_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['System', 'N_Records', 'Latency_Mean', 'Latency_CI_Lower',
                        'Latency_CI_Upper', 'Feasibility_Mean', 'Feasibility_CI_Lower',
                        'Feasibility_CI_Upper', 'Energy_Mean', 'Energy_CI_Lower',
                        'Energy_CI_Upper'])

        for system in sorted(analyzer.systems):
            if system not in metrics:
                continue

            m = metrics[system]
            lat_ci = m['latency_ci']
            feas_ci = m['feasible_ci']
            ene_ci = m['energy_ci']

            writer.writerow([
                system,
                m['n_records'],
                lat_ci[0], lat_ci[1], lat_ci[2],
                feas_ci[0], feas_ci[1], feas_ci[2],
                ene_ci[0], ene_ci[1], ene_ci[2],
            ])

    print(f"\n✓ Summary statistics saved to {summary_path}")

    # By-scenario summary
    scenario_group = {}
    for record in records:
        key = (record.system, record.scenario)
        if key not in scenario_group:
            scenario_group[key] = []
        scenario_group[key].append(record)

    scenario_path = args.output / 'summary_by_scenario.csv'
    with open(scenario_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['System', 'Scenario', 'N_Records', 'Latency_Mean',
                        'Feasibility_Pct', 'Energy_Mean'])

        for (system, scenario), recs in sorted(scenario_group.items()):
            lats = np.array([r.total_latency_ms for r in recs])
            feas = np.mean([1.0 if r.deadline_met else 0.0 for r in recs]) * 100
            engs = np.mean([r.total_energy_j for r in recs])

            writer.writerow([system, scenario, len(recs),
                            np.mean(lats), feas, engs])

    print(f"✓ Scenario breakdown saved to {scenario_path}")

    print("\n" + "=" * 70)
    print("Analysis complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
