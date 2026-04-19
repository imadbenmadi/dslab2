"""
Analysis and visualization of simulation results.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List

from .metrics import TaskRecord, MetricsCollector, SystemSummary
from .formulas import bootstrap_ci, wilcoxon_test
from .constants import SYSTEMS


class ResultsAnalyzer:
    """Analyze and visualize simulation results."""

    def __init__(self, records: List[TaskRecord]):
        self.records = records

    def compute_system_metrics(self, system: str) -> Dict:
        """Compute all metrics for a system."""
        sys_records = [r for r in self.records if r.system == system]
        if not sys_records:
            return {}

        latencies = [r.total_latency_ms for r in sys_records]
        energies = [r.total_energy_j for r in sys_records]
        feasible = [100.0 if r.deadline_met else 0.0 for r in sys_records]
        handoffs = [r for r in sys_records if r.handoff_occurred]
        hoff_ok = [100.0 if r.handoff_success else 0.0 for r in handoffs]

        return {
            "n": len(sys_records),
            "latency": bootstrap_ci(latencies),
            "energy": bootstrap_ci(energies),
            "feasibility": bootstrap_ci(feasible),
            "handoff_success": bootstrap_ci(hoff_ok) if hoff_ok else None,
            "p95_latency": np.percentile(latencies, 95),
        }

    def plot_latency_cdf(self, output_dir: Path = Path("experiments/figures")) -> None:
        """Plot latency CDF."""
        output_dir.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(6, 4))

        for system in SYSTEMS:
            sys_records = [r for r in self.records if r.system == system]
            if sys_records:
                latencies = sorted([r.total_latency_ms for r in sys_records])
                cdf = np.arange(1, len(latencies) + 1) / len(latencies)
                ax.plot(latencies, cdf, label=system, linewidth=2)

        ax.axvline(200, color="red", linestyle="--", label="Deadline (200ms)")
        ax.set_xlabel("Latency (ms)")
        ax.set_ylabel("CDF")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(output_dir / "fig1_latency_cdf.pdf", dpi=300)
        fig.savefig(output_dir / "fig1_latency_cdf.png", dpi=300)
        plt.close()

    def plot_feasibility_bars(self, output_dir: Path = Path("experiments/figures")) -> None:
        """Plot feasibility by scenario."""
        output_dir.mkdir(parents=True, exist_ok=True)

        scenarios = set(r.scenario for r in self.records)
        fig, ax = plt.subplots(figsize=(8, 4))

        for scenario in sorted(scenarios):
            feasibility_data = {}
            for system in SYSTEMS:
                sys_records = [r for r in self.records
                              if r.system == system and r.scenario == scenario]
                if sys_records:
                    feasible = sum(1 for r in sys_records if r.deadline_met) / len(sys_records) * 100
                    feasibility_data[system] = feasible

            x = np.arange(len(feasibility_data))
            ax.bar(x + len(list(scenarios)) * 0.1 * list(scenarios).index(scenario),
                  list(feasibility_data.values()), width=0.1, label=scenario)

        ax.set_ylabel("Feasibility (%)")
        ax.set_title("Feasibility by Scenario")
        ax.legend()
        fig.tight_layout()
        fig.savefig(output_dir / "fig2_feasibility_bars.pdf", dpi=300)
        plt.close()

    def plot_energy_latency_tradeoff(self, output_dir: Path = Path("experiments/figures")) -> None:
        """Plot energy-latency trade-off."""
        output_dir.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(6, 4))

        for system in SYSTEMS:
            sys_records = [r for r in self.records if r.system == system]
            if sys_records:
                avg_lat = np.mean([r.total_latency_ms for r in sys_records])
                avg_eng = np.mean([r.total_energy_j for r in sys_records])
                ax.scatter(avg_lat, avg_eng, label=system, s=100)

        ax.set_xlabel("Average Latency (ms)")
        ax.set_ylabel("Average Energy (J)")
        ax.set_title("Energy-Latency Trade-off")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(output_dir / "fig3_energy_latency.pdf", dpi=300)
        plt.close()

    def plot_step_breakdown(self, output_dir: Path = Path("experiments/figures")) -> None:
        """Plot per-step latency breakdown."""
        output_dir.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(6, 4))

        step_data = {}
        for system in SYSTEMS:
            sys_records = [r for r in self.records if r.system == system]
            if sys_records:
                step2_lat = np.mean([r.step2_latency_ms for r in sys_records])
                step3_lat = np.mean([r.step3_latency_ms for r in sys_records])
                step4_lat = np.mean([r.step4_latency_ms for r in sys_records])
                step5_lat = np.mean([r.step5_latency_ms for r in sys_records])
                step_data[system] = [step2_lat, step3_lat, step4_lat, step5_lat]

        systems_list = list(step_data.keys())
        x = np.arange(len(systems_list))
        step_names = ["Step 2", "Step 3", "Step 4", "Step 5"]
        colors = ["C0", "C1", "C2", "C3"]

        bottom = np.zeros(len(systems_list))
        for step_idx, step_name in enumerate(step_names):
            values = [step_data[sys][step_idx] for sys in systems_list]
            ax.bar(x, values, bottom=bottom, label=step_name, color=colors[step_idx])
            bottom += values

        ax.set_ylabel("Latency (ms)")
        ax.set_title("Per-Step Latency Breakdown")
        ax.set_xticks(x)
        ax.set_xticklabels(systems_list, rotation=45)
        ax.legend()
        fig.tight_layout()
        fig.savefig(output_dir / "fig9_step_breakdown.pdf", dpi=300)
        plt.close()

    def generate_summary_table(self, output_dir: Path = Path("experiments/results")) -> None:
        """Generate summary statistics table."""
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / "summary_overall.csv", "w") as f:
            f.write("System,Avg Latency (ms),Feasibility (%),Avg Energy (J),Handoff Success (%)\n")
            for system in SYSTEMS:
                metrics = self.compute_system_metrics(system)
                if metrics:
                    lat_mean, lat_low, lat_high = metrics["latency"]
                    feas_mean, feas_low, feas_high = metrics["feasibility"]
                    eng_mean, eng_low, eng_high = metrics["energy"]
                    hoff = metrics["handoff_success"]
                    hoff_str = f"{hoff[0]:.1f}" if hoff else "N/A"

                    f.write(f"{system},{lat_mean:.1f}±{(lat_high-lat_low)/2:.1f},"
                           f"{feas_mean:.1f}±{(feas_high-feas_low)/2:.1f},"
                           f"{eng_mean:.4f}±{(eng_high-eng_low)/2:.4f},"
                           f"{hoff_str}\n")

    def compute_significance_tests(self, output_dir: Path = Path("experiments/results")) -> None:
        """Compute Wilcoxon significance tests."""
        output_dir.mkdir(parents=True, exist_ok=True)

        proposed_records = [r for r in self.records if r.system == "proposed"]
        proposed_lat = [r.total_latency_ms for r in proposed_records]
        proposed_feas = [1.0 if r.deadline_met else 0.0 for r in proposed_records]

        with open(output_dir / "significance_tests.csv", "w") as f:
            f.write("Comparison System,Latency p-value,Feasibility p-value\n")
            for system in SYSTEMS:
                if system == "proposed":
                    continue
                sys_records = [r for r in self.records if r.system == system]
                sys_lat = [r.total_latency_ms for r in sys_records]
                sys_feas = [1.0 if r.deadline_met else 0.0 for r in sys_records]

                try:
                    _, p_lat = wilcoxon_test(proposed_lat, sys_lat)
                    _, p_feas = wilcoxon_test(proposed_feas, sys_feas)
                except:
                    p_lat, p_feas = 1.0, 1.0

                f.write(f"{system},{p_lat:.4f},{p_feas:.4f}\n")
