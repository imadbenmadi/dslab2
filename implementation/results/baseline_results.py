"""
Dynamic baseline tracking system - stores real results from each baseline run.
Replaces hardcoded static values with actual metric data.
"""

import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from threading import Lock


class BaselineResultsTracker:
    """Tracks real-time metrics for each baseline and proposed system."""

    def __init__(self, results_dir: str = "results"):
        self.results_dir = results_dir
        self.lock = Lock()
        self.current_run_metrics = {}
        self.baseline_cache = {}

        # Ensure results directory exists
        os.makedirs(results_dir, exist_ok=True)

    def start_run(self, system_type: str) -> None:
        """Initialize metrics tracking for a new simulation run."""
        with self.lock:
            self.current_run_metrics = {
                "system_type": system_type,
                "start_time": datetime.now().isoformat(),
                "tasks_total": 0,
                "tasks_deadline_met": 0,
                "total_latency_ms": 0.0,
                "total_energy_j": 0.0,
                "task_count": 0,
                "offloads_count": 0,
                "local_exec": 0,
                "fog_exec": 0,
                "cloud_exec": 0,
                "handoff_count": 0,
                "success_rate": 0.0,
                "avg_latency_ms": 0.0,
                "avg_energy_j": 0.0,
            }

    def record_task_completion(self, latency_ms: float, energy_j: float, 
                              deadline_met: bool, destination: str = None) -> None:
        """Record metrics for a completed task."""
        with self.lock:
            self.current_run_metrics["tasks_total"] += 1
            if deadline_met:
                self.current_run_metrics["tasks_deadline_met"] += 1
            self.current_run_metrics["total_latency_ms"] += latency_ms
            self.current_run_metrics["total_energy_j"] += energy_j
            self.current_run_metrics["task_count"] += 1

            if destination == "local":
                self.current_run_metrics["local_exec"] += 1
            elif destination in ["A", "B", "C", "D"]:
                self.current_run_metrics["fog_exec"] += 1
                self.current_run_metrics["offloads_count"] += 1
            elif destination == "cloud":
                self.current_run_metrics["cloud_exec"] += 1
                self.current_run_metrics["offloads_count"] += 1

    def record_handoff(self) -> None:
        """Record a handoff event."""
        with self.lock:
            self.current_run_metrics["handoff_count"] += 1

    def finalize_run(self, sim_duration_s: float) -> Dict[str, Any]:
        """Compute final metrics and save to file."""
        with self.lock:
            metrics = self.current_run_metrics.copy()

            # Calculate derived metrics
            task_count = metrics["tasks_total"]
            if task_count > 0:
                metrics["success_rate"] = (metrics["tasks_deadline_met"] / task_count) * 100.0
                metrics["avg_latency_ms"] = metrics["total_latency_ms"] / task_count
                metrics["avg_energy_j"] = metrics["total_energy_j"] / task_count
            else:
                metrics["success_rate"] = 0.0
                metrics["avg_latency_ms"] = 0.0
                metrics["avg_energy_j"] = 0.0

            metrics["end_time"] = datetime.now().isoformat()
            metrics["duration_s"] = sim_duration_s

            # Save to disk
            system_type = metrics["system_type"]
            results_file = os.path.join(self.results_dir, f"baseline_{system_type}_results.jsonl")
            try:
                with open(results_file, "a") as f:
                    f.write(json.dumps(metrics) + "\n")
            except Exception as e:
                print(f"[Baseline] Failed to save results: {e}")

            # Update cache for quick access
            self.baseline_cache[system_type] = metrics
            self.current_run_metrics = {}

            return metrics

    def get_baseline_summary(self) -> Dict[str, Any]:
        """
        Get latest aggregated results for baselines.
        Returns: {baseline1, baseline2, baseline3, proposed} with their last known metrics.
        """
        with self.lock:
            summary = {}

            # Try to load latest results for each system type
            for system_type in ["baseline1", "baseline2", "baseline3", "proposed"]:
                result_file = os.path.join(self.results_dir, f"baseline_{system_type}_results.jsonl")
                if os.path.exists(result_file):
                    try:
                        with open(result_file, "r") as f:
                            last_line = None
                            for line in f:
                                last_line = line.strip()
                            if last_line:
                                data = json.loads(last_line)
                                summary[system_type] = {
                                    "name": self._system_name(system_type),
                                    "successRate": data.get("success_rate", 0.0),
                                    "avgLatency": data.get("avg_latency_ms", 0.0),
                                    "totalEnergy": data.get("avg_energy_j", 0.0) * data.get("tasks_total", 1),
                                    "lastRun": data.get("end_time", ""),
                                    "tasksCompleted": data.get("tasks_total", 0),
                                }
                    except Exception as e:
                        print(f"[Baseline] Failed to load {system_type}: {e}")

            # Fallback to cache if files don't exist yet
            if not summary:
                for system_type in ["baseline1", "baseline2", "baseline3", "proposed"]:
                    if system_type in self.baseline_cache:
                        data = self.baseline_cache[system_type]
                        summary[system_type] = {
                            "name": self._system_name(system_type),
                            "successRate": data.get("success_rate", 0.0),
                            "avgLatency": data.get("avg_latency_ms", 0.0),
                            "totalEnergy": data.get("avg_energy_j", 0.0) * data.get("tasks_total", 1),
                            "lastRun": data.get("end_time", ""),
                            "tasksCompleted": data.get("tasks_total", 0),
                        }

            return summary

    @staticmethod
    def _system_name(system_type: str) -> str:
        """Map system type to display name."""
        names = {
            "baseline1": "Pure NSGA-II",
            "baseline2": "TOF + NSGA-II",
            "baseline3": "TOF + MMDE-NSGA-II",
            "proposed": "Proposed (MMDE-NSGA-II + Agents + Handoff)",
        }
        return names.get(system_type, system_type)

    def get_system_comparison(self) -> Dict[str, Any]:
        """Get comparison table for all systems."""
        summary = self.get_baseline_summary()
        return {
            "baseline1": summary.get("baseline1", {}),
            "baseline2": summary.get("baseline2", {}),
            "baseline3": summary.get("baseline3", {}),
            "proposed": summary.get("proposed", {}),
        }


# Singleton instance
_tracker: Optional[BaselineResultsTracker] = None


def get_baseline_tracker() -> BaselineResultsTracker:
    """Get singleton results tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = BaselineResultsTracker()
    return _tracker
