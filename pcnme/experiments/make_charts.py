"""
PCNME Results Visualization
Generates publication-quality figures (currently 4: Fig 1/2/3/9).

Usage:
    python experiments/make_charts.py \\
        --input experiments/results/ \\
        --output experiments/figures/ \\
        --dpi 300
"""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from pcnme import MetricsCollector, ResultsAnalyzer
from pcnme.progress import progress


def main():
    parser = argparse.ArgumentParser(
        description="PCNME Results Visualization"
    )
    parser.add_argument('--input', type=Path,
                       default='experiments/results/',
                       help='Input directory with raw_results.csv')
    parser.add_argument('--output', type=Path,
                       default='experiments/figures/',
                       help='Output directory for figures')
    parser.add_argument('--dpi', type=int, default=300,
                       help='Figure DPI')

    args = parser.parse_args()

    print("=" * 70)
    print("PCNME RESULTS VISUALIZATION")
    print("=" * 70)

    # Load records
    records_path = args.input / 'raw_results.csv'
    print(f"\nLoading results from {records_path}...")
    records = MetricsCollector.load_csv(records_path)
    print(f"✓ Loaded {len(records)} records")

    # Create analyzer
    analyzer = ResultsAnalyzer(records)

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Generate figures
    print(f"\nGenerating figures to {args.output}...\n")

    figures = [
        ("Fig 1: Latency CDF", analyzer.plot_latency_cdf),
        ("Fig 2: Feasibility bars by scenario", analyzer.plot_feasibility_bars),
        ("Fig 3: Energy-Latency trade-off", analyzer.plot_energy_latency_tradeoff),
        ("Fig 9: Per-step latency breakdown", analyzer.plot_step_breakdown),
    ]

    for label, fn in progress(figures, desc="Figures", unit="fig", total=len(figures)):
        print(f"  {label}...")
        fn(args.output)

    print("\n" + "=" * 70)
    print("Visualization complete!")
    print(f"Figures saved to: {args.output}")
    print("=" * 70)


if __name__ == '__main__':
    main()
