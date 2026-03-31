"""Plotting and visualization functions for results analysis."""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from typing import Dict, List, Any


def plot_all(results: Dict[str, Any]):
    """
    Generate comprehensive comparison plots for all metrics.
    
    Args:
        results: Dictionary with 'latency_ms', 'energy_j', 'deadline_success_pct', etc.
    """
    if not results:
        print("No results to plot")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Smart City Task Offloading - Performance Analysis', fontsize=16, fontweight='bold')
    
    if 'latency_ms' in results:
        axes[0, 0].plot(results['latency_ms'], marker='o', color='blue', linewidth=2)
        axes[0, 0].set_title('Average Latency Over Time', fontweight='bold')
        axes[0, 0].set_ylabel('Latency (ms)')
        axes[0, 0].set_xlabel('Time (s)')
        axes[0, 0].grid(True, alpha=0.3)
    
    if 'energy_j' in results:
        axes[0, 1].plot(results['energy_j'], marker='s', color='orange', linewidth=2)
        axes[0, 1].set_title('Average Energy Consumption', fontweight='bold')
        axes[0, 1].set_ylabel('Energy (J)')
        axes[0, 1].set_xlabel('Time (s)')
        axes[0, 1].grid(True, alpha=0.3)
    
    if 'deadline_success_pct' in results:
        axes[1, 0].plot(results['deadline_success_pct'], marker='^', color='green', linewidth=2)
        axes[1, 0].set_title('Deadline Success Rate', fontweight='bold')
        axes[1, 0].set_ylabel('Success Rate (%)')
        axes[1, 0].set_xlabel('Time (s)')
        axes[1, 0].set_ylim([0, 105])
        axes[1, 0].grid(True, alpha=0.3)
    
    axes[1, 1].axis('off')
    summary_text = "System Performance Summary\n" + "="*30 + "\n"
    
    if 'avg_latency_ms' in results:
        summary_text += f"Avg Latency: {results['avg_latency_ms']:.1f} ms\n"
    if 'avg_energy_j' in results:
        summary_text += f"Avg Energy: {results['avg_energy_j']:.3f} J\n"
    if 'deadline_success_rate' in results:
        summary_text += f"Deadline Success: {results['deadline_success_rate']:.1f}%\n"
    if 'total_tasks_completed' in results:
        summary_text += f"Tasks Completed: {results['total_tasks_completed']}\n"
    
    axes[1, 1].text(0.1, 0.5, summary_text, fontsize=12, family='monospace',
                   verticalalignment='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    return fig


def plot_comparison(baseline_results: Dict[str, Dict]) -> plt.Figure:
    """
    Compare performance across multiple systems.
    
    Args:
        baseline_results: {system_name: {metric: value}}
    """
    if not baseline_results:
        print("No comparison data provided")
        return None
    
    systems = list(baseline_results.keys())
    latencies = [baseline_results[s].get('avg_latency_ms', 0) for s in systems]
    energies = [baseline_results[s].get('avg_energy_j', 0) for s in systems]
    feasibility = [baseline_results[s].get('deadline_success_rate', 0) for s in systems]
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle('System Comparison: Baselines vs. Proposed', fontsize=16, fontweight='bold')
    
    colors = ['red' if i < len(systems) - 1 else 'green' for i in range(len(systems))]
    axes[0].bar(systems, latencies, color=colors, alpha=0.7, edgecolor='black')
    axes[0].set_title('Average Latency', fontweight='bold')
    axes[0].set_ylabel('Latency (ms)')
    axes[0].tick_params(axis='x', rotation=45)
    axes[0].grid(True, alpha=0.3, axis='y')
    
    axes[1].bar(systems, energies, color=colors, alpha=0.7, edgecolor='black')
    axes[1].set_title('Average Energy', fontweight='bold')
    axes[1].set_ylabel('Energy (J)')
    axes[1].tick_params(axis='x', rotation=45)
    axes[1].grid(True, alpha=0.3, axis='y')
    
    axes[2].bar(systems, feasibility, color=colors, alpha=0.7, edgecolor='black')
    axes[2].set_title('Deadline Success Rate', fontweight='bold')
    axes[2].set_ylabel('Success Rate (%)')
    axes[2].set_ylim([0, 105])
    axes[2].tick_params(axis='x', rotation=45)
    axes[2].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    return fig
