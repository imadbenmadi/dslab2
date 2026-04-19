"""
PCNME Results Visualization and Analysis
Generates publication-quality figures and tables.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from .constants import SYSTEM_STYLES, CHART_DPI, CHART_FONTSIZE, CHART_FIGSIZE
from .formulas import bootstrap_ci, wilcoxon_test


class ResultsAnalyzer:
    """Analyzes and visualizes simulation results."""

    def __init__(self, records: list):
        self.records = records
        self.systems = list(set(r.system for r in records))
        self.scenarios = list(set(r.scenario for r in records))

    def group_by_system(self):
        """Group records by system."""
        grouped = {sys: [] for sys in self.systems}
        for record in self.records:
            grouped[record.system].append(record)
        return grouped

    def group_by_scenario(self):
        """Group records by scenario."""
        grouped = {sce: [] for sce in self.scenarios}
        for record in self.records:
            grouped[record.scenario].append(record)
        return grouped

    def compute_system_metrics(self):
        """Compute metrics for each system."""
        grouped = self.group_by_system()
        metrics = {}

        for system, records in grouped.items():
            latencies = np.array([r.total_latency_ms for r in records])
            energies = np.array([r.total_energy_j for r in records])
            feasible = np.array([1.0 if r.deadline_met else 0.0
                                for r in records])

            handoff_recs = [r for r in records if r.handoff_occurred]
            if handoff_recs:
                handoff_success = np.array([1.0 if r.handoff_success else 0.0
                                           for r in handoff_recs])
            else:
                handoff_success = np.array([])

            metrics[system] = {
                'n_records': len(records),
                'latency': latencies,
                'energy': energies,
                'feasible': feasible,
                'handoff_success': handoff_success,
                'latency_ci': bootstrap_ci(latencies),
                'energy_ci': bootstrap_ci(energies),
                'feasible_ci': bootstrap_ci(feasible * 100),
            }

        return metrics

    def plot_latency_cdf(self, output_path: Path = None):
        """
        Figure 1: Latency CDF
        One curve per system, vertical line at 200ms deadline.
        """
        grouped = self.group_by_system()

        plt.figure(figsize=CHART_FIGSIZE, dpi=CHART_DPI)

        for system in sorted(self.systems):
            if system not in grouped:
                continue

            latencies = sorted([r.total_latency_ms for r in grouped[system]])
            cdf = np.arange(1, len(latencies) + 1) / len(latencies)

            style = SYSTEM_STYLES.get(system, {})
            plt.plot(latencies, cdf, label=style.get('label', system),
                     linestyle=style.get('ls', '-'),
                     marker=style.get('marker', 'o'),
                     linewidth=style.get('lw', 1.5))

        plt.axvline(200, color='red', linestyle='--', label='Deadline (200ms)')
        plt.xlabel('Latency (ms)', fontsize=CHART_FONTSIZE)
        plt.ylabel('CDF', fontsize=CHART_FONTSIZE)
        plt.title('Latency CDF Across All Systems', fontsize=CHART_FONTSIZE + 1)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path / 'fig1_latency_cdf.pdf', dpi=CHART_DPI)
            plt.savefig(output_path / 'fig1_latency_cdf.png', dpi=CHART_DPI)

        plt.close()

    def plot_feasibility_bars(self, output_path: Path = None):
        """
        Figure 2: Feasibility rate by scenario with error bars.
        """
        metrics = self.compute_system_metrics()

        fig, axes = plt.subplots(1, len(self.scenarios), figsize=(15, 4),
                                 dpi=CHART_DPI)
        if len(self.scenarios) == 1:
            axes = [axes]

        grouped_scenario = self.group_by_scenario()

        for ax_idx, scenario in enumerate(sorted(self.scenarios)):
            ax = axes[ax_idx]

            # Group by system for this scenario
            scenario_records = grouped_scenario[scenario]
            sys_feasibility = {}

            for system in self.systems:
                sys_scenario_records = [r for r in scenario_records
                                        if r.system == system]
                if sys_scenario_records:
                    feas = [1.0 if r.deadline_met else 0.0
                           for r in sys_scenario_records]
                    sys_feasibility[system] = bootstrap_ci(np.array(feas) * 100)

            # Plot bars
            systems_list = sorted(sys_feasibility.keys())
            means = [sys_feasibility[s][0] for s in systems_list]
            cis_lower = [sys_feasibility[s][1] for s in systems_list]
            cis_upper = [sys_feasibility[s][2] for s in systems_list]

            x = np.arange(len(systems_list))
            errors = [
                np.array(means) - np.array(cis_lower),
                np.array(cis_upper) - np.array(means)
            ]

            ax.bar(x, means, yerr=errors, capsize=5, alpha=0.7)
            ax.set_ylabel('Feasibility (%)', fontsize=CHART_FONTSIZE)
            ax.set_title(scenario.replace('_', ' ').title(),
                        fontsize=CHART_FONTSIZE)
            ax.set_xticks(x)
            ax.set_xticklabels([s.replace('_', '\n') for s in systems_list],
                              fontsize=9, rotation=45, ha='right')
            ax.set_ylim([0, 105])
            ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path / 'fig2_feasibility_bars.pdf', dpi=CHART_DPI)
            plt.savefig(output_path / 'fig2_feasibility_bars.png', dpi=CHART_DPI)

        plt.close()

    def plot_energy_latency_tradeoff(self, output_path: Path = None):
        """
        Figure 3: Energy-Latency trade-off scatter with error ellipses.
        """
        metrics = self.compute_system_metrics()

        plt.figure(figsize=CHART_FIGSIZE, dpi=CHART_DPI)

        for system in sorted(self.systems):
            if system not in metrics:
                continue

            m = metrics[system]
            avg_lat = m['latency_ci'][0]
            avg_ene = m['energy_ci'][0]

            std_lat = np.std(m['latency'])
            std_ene = np.std(m['energy'])

            style = SYSTEM_STYLES.get(system, {})
            plt.errorbar(avg_lat, avg_ene,
                        xerr=std_lat, yerr=std_ene,
                        fmt=style.get('marker', 'o'),
                        label=style.get('label', system),
                        capsize=5, markersize=8)

        plt.xlabel('Average Latency (ms)', fontsize=CHART_FONTSIZE)
        plt.ylabel('Average Energy (J)', fontsize=CHART_FONTSIZE)
        plt.title('Energy-Latency Trade-off', fontsize=CHART_FONTSIZE + 1)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path / 'fig3_energy_latency.pdf', dpi=CHART_DPI)
            plt.savefig(output_path / 'fig3_energy_latency.png', dpi=CHART_DPI)

        plt.close()

    def plot_step_breakdown(self, output_path: Path = None):
        """
        Figure 9: Per-step latency breakdown (stacked bars).
        Most insightful for understanding why proposed system works.
        """
        metrics = self.compute_system_metrics()

        fig, ax = plt.subplots(figsize=CHART_FIGSIZE, dpi=CHART_DPI)

        systems_list = sorted(self.systems)
        x = np.arange(len(systems_list))

        # Compute average per-step latencies
        step_latencies = {sys: {'step2': [], 'step3': [], 'step4': [],
                               'step5': []}
                         for sys in systems_list}

        for system in systems_list:
            system_records = [r for r in self.records if r.system == system]
            for record in system_records:
                step_latencies[system]['step2'].append(record.step2_latency_ms)
                step_latencies[system]['step3'].append(record.step3_latency_ms)
                step_latencies[system]['step4'].append(record.step4_latency_ms)
                step_latencies[system]['step5'].append(record.step5_latency_ms)

        # Average per system
        avg_step2 = [np.mean(step_latencies[s]['step2']) for s in systems_list]
        avg_step3 = [np.mean(step_latencies[s]['step3']) for s in systems_list]
        avg_step4 = [np.mean(step_latencies[s]['step4']) for s in systems_list]
        avg_step5 = [np.mean(step_latencies[s]['step5']) for s in systems_list]

        # Stacked bars
        ax.bar(x, avg_step2, label='Step 2', alpha=0.8)
        ax.bar(x, avg_step3, bottom=np.array(avg_step2), label='Step 3', alpha=0.8)
        ax.bar(x, avg_step4,
              bottom=np.array(avg_step2) + np.array(avg_step3),
              label='Step 4', alpha=0.8)
        ax.bar(x, avg_step5,
              bottom=np.array(avg_step2) + np.array(avg_step3) + np.array(avg_step4),
              label='Step 5', alpha=0.8)

        ax.set_ylabel('Latency (ms)', fontsize=CHART_FONTSIZE)
        ax.set_title('Per-Step Latency Breakdown', fontsize=CHART_FONTSIZE + 1)
        ax.set_xticks(x)
        ax.set_xticklabels([s.replace('_', '\n') for s in systems_list],
                          fontsize=10, rotation=45, ha='right')
        ax.legend(fontsize=CHART_FONTSIZE)
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path / 'fig9_step_breakdown.pdf', dpi=CHART_DPI)
            plt.savefig(output_path / 'fig9_step_breakdown.png', dpi=CHART_DPI)

        plt.close()

    def generate_summary_table(self):
        """Generate summary statistics table."""
        metrics = self.compute_system_metrics()

        print("\n" + "=" * 120)
        print("PCNME RESULTS SUMMARY")
        print("=" * 120)

        print(f"{'System':<20} {'N':<6} {'Avg Lat (ms)':<20} "
              f"{'Feas %':<15} {'Avg Eng (J)':<20} {'HO Success %':<15}")
        print("-" * 120)

        for system in sorted(self.systems):
            if system not in metrics:
                continue

            m = metrics[system]
            lat_mean, lat_ci_l, lat_ci_u = m['latency_ci']
            feas_mean, feas_ci_l, feas_ci_u = m['feasible_ci']
            ene_mean, ene_ci_l, ene_ci_u = m['energy_ci']

            lat_str = f"{lat_mean:.1f}±{lat_ci_u-lat_mean:.1f}"
            feas_str = f"{feas_mean:.1f}±{feas_ci_u-feas_mean:.1f}"
            ene_str = f"{ene_mean:.4f}±{ene_ci_u-ene_mean:.4f}"

            if len(m['handoff_success']) > 0:
                ho_mean = np.mean(m['handoff_success']) * 100
                ho_str = f"{ho_mean:.1f}"
            else:
                ho_str = "N/A"

            print(f"{system:<20} {m['n_records']:<6} {lat_str:<20} "
                  f"{feas_str:<15} {ene_str:<20} {ho_str:<15}")

        print("=" * 120 + "\n")

    def compute_significance_tests(self):
        """Compute Wilcoxon tests for proposed vs others."""
        print("\n" + "=" * 80)
        print("STATISTICAL SIGNIFICANCE TESTS (Wilcoxon signed-rank)")
        print("Comparing 'proposed' vs other systems")
        print("H0: proposed latency < other latency (alternative='less')")
        print("=" * 80)

        proposed_lat = np.array([r.total_latency_ms
                                for r in self.records if r.system == 'proposed'])

        for system in sorted(self.systems):
            if system == 'proposed':
                continue

            other_lat = np.array([r.total_latency_ms
                                 for r in self.records if r.system == system])

            if len(proposed_lat) != len(other_lat):
                n = min(len(proposed_lat), len(other_lat))
                proposed_lat_test = proposed_lat[:n]
                other_lat_test = other_lat[:n]
            else:
                proposed_lat_test = proposed_lat
                other_lat_test = other_lat

            stat, p_value = wilcoxon_test(proposed_lat_test, other_lat_test)

            significance = "SIGNIFICANT" if p_value < 0.05 else "NOT significant"
            print(f"{system:<20} p-value={p_value:.6f} [{significance}]")

        print("=" * 80 + "\n")
