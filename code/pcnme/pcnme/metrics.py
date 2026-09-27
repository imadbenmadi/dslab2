"""
Metrics data structures and collection utilities.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
import csv
import numpy as np
from pathlib import Path

from .constants import SEEDS


@dataclass
class TaskRecord:
    """Complete metrics for a single task execution."""
    # Identifiers
    task_id: str
    system: str
    seed: int
    scenario: str
    vehicle_id: str
    sim_time_s: float

    # Per-task outcomes
    total_latency_ms: float
    total_energy_j: float
    deadline_met: bool

    # Per-step breakdown (steps 2, 3, 4, 5)
    step2_latency_ms: float
    step3_latency_ms: float
    step4_latency_ms: float
    step5_latency_ms: float
    step2_energy_j: float
    step3_energy_j: float
    step4_energy_j: float
    step5_energy_j: float
    step2_dest: str
    step3_dest: str
    step5_dest: str

    # EC classification
    n_boulders: int
    n_pebbles: int

    # Mobility and handoff
    handoff_occurred: bool
    handoff_mode: str  # direct / proactive / htb / none
    handoff_success: bool
    t_exit_at_decision: float

    # Fog state at decision time
    fog_A_load: float
    fog_B_load: float
    fog_C_load: float
    fog_D_load: float
    fog_A_queue: int
    fog_B_queue: int
    fog_C_queue: int
    fog_D_queue: int

    # Agent internals (optional)
    agent_q_max: Optional[float] = None
    agent_epsilon: Optional[float] = None
    agent_reward: Optional[float] = None
    bc_loss_final: Optional[float] = None
    online_updates: Optional[int] = None


@dataclass
class MetricsCollector:
    """Batch collection of task records."""
    records: List[TaskRecord] = field(default_factory=list)

    def add_record(self, record: TaskRecord) -> None:
        """Add a task record."""
        self.records.append(record)

    def save_csv(self, filepath: Path) -> None:
        """Save all records to CSV."""
        if not self.records:
            return
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=asdict(self.records[0]).keys())
            writer.writeheader()
            for record in self.records:
                writer.writerow(asdict(record))

    @staticmethod
    def load_csv(filepath: Path) -> "MetricsCollector":
        """Load records from CSV."""
        collector = MetricsCollector()
        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert types
                row["seed"] = int(row["seed"])
                row["sim_time_s"] = float(row["sim_time_s"])
                row["total_latency_ms"] = float(row["total_latency_ms"])
                row["total_energy_j"] = float(row["total_energy_j"])
                row["deadline_met"] = row["deadline_met"].lower() == "true"
                row["step2_latency_ms"] = float(row["step2_latency_ms"])
                row["step3_latency_ms"] = float(row["step3_latency_ms"])
                row["step4_latency_ms"] = float(row["step4_latency_ms"])
                row["step5_latency_ms"] = float(row["step5_latency_ms"])
                row["step2_energy_j"] = float(row["step2_energy_j"])
                row["step3_energy_j"] = float(row["step3_energy_j"])
                row["step4_energy_j"] = float(row["step4_energy_j"])
                row["step5_energy_j"] = float(row["step5_energy_j"])
                row["n_boulders"] = int(row["n_boulders"])
                row["n_pebbles"] = int(row["n_pebbles"])
                row["handoff_occurred"] = row["handoff_occurred"].lower() == "true"
                row["handoff_success"] = row["handoff_success"].lower() == "true"
                row["t_exit_at_decision"] = float(row["t_exit_at_decision"])
                row["fog_A_load"] = float(row["fog_A_load"])
                row["fog_B_load"] = float(row["fog_B_load"])
                row["fog_C_load"] = float(row["fog_C_load"])
                row["fog_D_load"] = float(row["fog_D_load"])
                row["fog_A_queue"] = int(row["fog_A_queue"])
                row["fog_B_queue"] = int(row["fog_B_queue"])
                row["fog_C_queue"] = int(row["fog_C_queue"])
                row["fog_D_queue"] = int(row["fog_D_queue"])
                
                # Optional fields
                if row["agent_q_max"]:
                    row["agent_q_max"] = float(row["agent_q_max"])
                else:
                    row["agent_q_max"] = None
                if row["agent_epsilon"]:
                    row["agent_epsilon"] = float(row["agent_epsilon"])
                else:
                    row["agent_epsilon"] = None
                if row["agent_reward"]:
                    row["agent_reward"] = float(row["agent_reward"])
                else:
                    row["agent_reward"] = None
                if row["bc_loss_final"]:
                    row["bc_loss_final"] = float(row["bc_loss_final"])
                else:
                    row["bc_loss_final"] = None
                if row["online_updates"]:
                    row["online_updates"] = int(row["online_updates"])
                else:
                    row["online_updates"] = None
                
                collector.add_record(TaskRecord(**row))
        return collector


@dataclass
class SystemSummary:
    """Summary statistics per system."""
    system: str
    n_runs: int
    avg_latency_ms: tuple  # (mean, ci_low, ci_high)
    avg_energy_j: tuple
    feasibility_pct: tuple
    handoff_success_pct: Optional[tuple]
    p95_latency_ms: float

    @staticmethod
    def compute_from_records(records: List[TaskRecord], system: str):
        """Compute summary for a specific system."""
        from .formulas import bootstrap_ci

        sys_records = [r for r in records if r.system == system]
        if not sys_records:
            return None

        latencies = [r.total_latency_ms for r in sys_records]
        energies = [r.total_energy_j for r in sys_records]
        feasible = [100.0 if r.deadline_met else 0.0 for r in sys_records]
        handoffs = [r for r in sys_records if r.handoff_occurred]
        hoff_ok = [100.0 if r.handoff_success else 0.0 for r in handoffs]

        return SystemSummary(
            system=system,
            n_runs=len(sys_records),
            avg_latency_ms=bootstrap_ci(latencies),
            avg_energy_j=bootstrap_ci(energies),
            feasibility_pct=bootstrap_ci(feasible),
            handoff_success_pct=bootstrap_ci(hoff_ok) if hoff_ok else None,
            p95_latency_ms=float(np.percentile(latencies, 95)),
        )
