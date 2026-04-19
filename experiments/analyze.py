"""
Statistical analysis script.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pcnme import MetricsCollector, ResultsAnalyzer, SYSTEMS


def main():
    parser = argparse.ArgumentParser(description="Analyze simulation results")
    parser.add_argument("--input", type=str, default="experiments/results/raw_results.csv",
                       help="Input CSV with results")
    parser.add_argument("--output", type=str, default="experiments/results/",
                       help="Output directory for analysis")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("[1/3] Loading results...")
    collector = MetricsCollector.load_csv(input_path)
    print(f"      Loaded {len(collector.records)} task records")

    print("[2/3] Computing metrics...")
    analyzer = ResultsAnalyzer(collector.records)
    analyzer.generate_summary_table(output_dir)
    analyzer.compute_significance_tests(output_dir)

    print("[3/3] Displaying summary...")
    print("\n=== SUMMARY BY SYSTEM ===\n")
    for system in SYSTEMS:
        metrics = analyzer.compute_system_metrics(system)
        if metrics:
            print(f"{system:20s}:")
            lat_mean, lat_low, lat_high = metrics["latency"]
            feas_mean, feas_low, feas_high = metrics["feasibility"]
            eng_mean, eng_low, eng_high = metrics["energy"]
            print(f"  Latency:     {lat_mean:7.1f} ± {(lat_high-lat_low)/2:5.1f} ms")
            print(f"  Feasibility: {feas_mean:7.1f} ± {(feas_high-feas_low)/2:5.1f} %")
            print(f"  Energy:      {eng_mean:7.4f} ± {(eng_high-eng_low)/2:5.4f} J")
            print()

    print(f"✓ Analysis complete. Results saved to {output_dir}")


if __name__ == "__main__":
    main()
