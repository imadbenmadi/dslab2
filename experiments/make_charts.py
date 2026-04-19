"""
Generate publication-quality figures.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pcnme import MetricsCollector, ResultsAnalyzer


def main():
    parser = argparse.ArgumentParser(description="Generate figures from results")
    parser.add_argument("--input", type=str, default="experiments/results/",
                       help="Input directory with results")
    parser.add_argument("--output", type=str, default="experiments/figures/",
                       help="Output directory for figures")
    parser.add_argument("--dpi", type=int, default=300,
                       help="DPI for saved figures")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("[1/2] Loading results...")
    results_file = input_dir / "raw_results.csv"
    if not results_file.exists():
        print(f"ERROR: {results_file} not found")
        return

    collector = MetricsCollector.load_csv(results_file)
    print(f"      Loaded {len(collector.records)} records")

    print("[2/2] Generating figures...")
    analyzer = ResultsAnalyzer(collector.records)

    analyzer.plot_latency_cdf(output_dir)
    print("      ✓ Fig 1: Latency CDF")

    analyzer.plot_feasibility_bars(output_dir)
    print("      ✓ Fig 2: Feasibility by scenario")

    analyzer.plot_energy_latency_tradeoff(output_dir)
    print("      ✓ Fig 3: Energy-latency trade-off")

    analyzer.plot_step_breakdown(output_dir)
    print("      ✓ Fig 9: Per-step latency breakdown")

    print(f"\n✓ Figures saved to {output_dir}")


if __name__ == "__main__":
    main()
