"""
PCNME Metrics Collection and Data Structures
"""

from dataclasses import dataclass, field
from typing import Optional
import csv
from pathlib import Path
import numpy as np


@dataclass
class TaskRecord:
    """
    Complete record of a single task execution.
    Used for comprehensive results collection across all systems.
    """
    # ========== IDENTIFIERS ==========
    task_id:            str
    system:             str
    seed:               int
    scenario:           str
    vehicle_id:         str
    sim_time_s:         float

    # ========== PER-TASK OUTCOMES ==========
    total_latency_ms:   float
    total_energy_j:     float
    deadline_met:       bool          # total_latency_ms <= 200

    # ========== PER-STEP BREAKDOWN ==========
    step2_latency_ms:   float
    step3_latency_ms:   float
    step4_latency_ms:   float         # always cloud
    step5_latency_ms:   float
    step2_energy_j:     float
    step3_energy_j:     float
    step4_energy_j:     float
    step5_energy_j:     float
    step2_dest:         str           # fog_A/B/C/D or cloud
    step3_dest:         str
    step5_dest:         str

    # ========== EC CLASSIFICATION ==========
    n_boulders:         int           # steps with EC >= 1.0
    n_pebbles:          int           # steps with EC < 1.0

    # ========== MOBILITY ==========
    handoff_occurred:   bool
    handoff_mode:       str           # direct / proactive / htb / none
    handoff_success:    bool
    t_exit_at_decision: float         # T_exit value when decision was made

    # ========== FOG STATE AT DECISION TIME ==========
    fog_A_load:         float
    fog_B_load:         float
    fog_C_load:         float
    fog_D_load:         float
    fog_A_queue:        int
    fog_B_queue:        int
    fog_C_queue:        int
    fog_D_queue:        int

    # ========== AGENT INTERNALS (proposed/ablation only) ==========
    agent_q_max:        Optional[float] = None
    agent_epsilon:      Optional[float] = None
    agent_reward:       Optional[float] = None
    bc_loss_final:      Optional[float] = None
    online_updates:     Optional[int]   = None

    def to_dict(self):
        """Convert record to dictionary for CSV export."""
        return {
            'task_id': self.task_id,
            'system': self.system,
            'seed': self.seed,
            'scenario': self.scenario,
            'vehicle_id': self.vehicle_id,
            'sim_time_s': self.sim_time_s,
            'total_latency_ms': self.total_latency_ms,
            'total_energy_j': self.total_energy_j,
            'deadline_met': int(self.deadline_met),
            'step2_latency_ms': self.step2_latency_ms,
            'step3_latency_ms': self.step3_latency_ms,
            'step4_latency_ms': self.step4_latency_ms,
            'step5_latency_ms': self.step5_latency_ms,
            'step2_energy_j': self.step2_energy_j,
            'step3_energy_j': self.step3_energy_j,
            'step4_energy_j': self.step4_energy_j,
            'step5_energy_j': self.step5_energy_j,
            'step2_dest': self.step2_dest,
            'step3_dest': self.step3_dest,
            'step5_dest': self.step5_dest,
            'n_boulders': self.n_boulders,
            'n_pebbles': self.n_pebbles,
            'handoff_occurred': int(self.handoff_occurred),
            'handoff_mode': self.handoff_mode,
            'handoff_success': int(self.handoff_success),
            't_exit_at_decision': self.t_exit_at_decision,
            'fog_A_load': self.fog_A_load,
            'fog_B_load': self.fog_B_load,
            'fog_C_load': self.fog_C_load,
            'fog_D_load': self.fog_D_load,
            'fog_A_queue': self.fog_A_queue,
            'fog_B_queue': self.fog_B_queue,
            'fog_C_queue': self.fog_C_queue,
            'fog_D_queue': self.fog_D_queue,
            'agent_q_max': self.agent_q_max,
            'agent_epsilon': self.agent_epsilon,
            'agent_reward': self.agent_reward,
            'bc_loss_final': self.bc_loss_final,
            'online_updates': self.online_updates,
        }

    @staticmethod
    def from_dict(d):
        """Reconstruct TaskRecord from dictionary."""
        return TaskRecord(
            task_id=d['task_id'],
            system=d['system'],
            seed=int(d['seed']),
            scenario=d['scenario'],
            vehicle_id=d['vehicle_id'],
            sim_time_s=float(d['sim_time_s']),
            total_latency_ms=float(d['total_latency_ms']),
            total_energy_j=float(d['total_energy_j']),
            deadline_met=bool(int(d['deadline_met'])),
            step2_latency_ms=float(d['step2_latency_ms']),
            step3_latency_ms=float(d['step3_latency_ms']),
            step4_latency_ms=float(d['step4_latency_ms']),
            step5_latency_ms=float(d['step5_latency_ms']),
            step2_energy_j=float(d['step2_energy_j']),
            step3_energy_j=float(d['step3_energy_j']),
            step4_energy_j=float(d['step4_energy_j']),
            step5_energy_j=float(d['step5_energy_j']),
            step2_dest=d['step2_dest'],
            step3_dest=d['step3_dest'],
            step5_dest=d['step5_dest'],
            n_boulders=int(d['n_boulders']),
            n_pebbles=int(d['n_pebbles']),
            handoff_occurred=bool(int(d['handoff_occurred'])),
            handoff_mode=d['handoff_mode'],
            handoff_success=bool(int(d['handoff_success'])),
            t_exit_at_decision=float(d['t_exit_at_decision']),
            fog_A_load=float(d['fog_A_load']),
            fog_B_load=float(d['fog_B_load']),
            fog_C_load=float(d['fog_C_load']),
            fog_D_load=float(d['fog_D_load']),
            fog_A_queue=int(d['fog_A_queue']),
            fog_B_queue=int(d['fog_B_queue']),
            fog_C_queue=int(d['fog_C_queue']),
            fog_D_queue=int(d['fog_D_queue']),
            agent_q_max=float(d['agent_q_max']) if d.get('agent_q_max') else None,
            agent_epsilon=float(d['agent_epsilon']) if d.get('agent_epsilon') else None,
            agent_reward=float(d['agent_reward']) if d.get('agent_reward') else None,
            bc_loss_final=float(d['bc_loss_final']) if d.get('bc_loss_final') else None,
            online_updates=int(d['online_updates']) if d.get('online_updates') else None,
        )


class MetricsCollector:
    """Collects and exports results from all systems."""

    def __init__(self):
        self.records = []

    def add_record(self, record: TaskRecord):
        """Add a task record."""
        self.records.append(record)

    def save_csv(self, filepath: Path):
        """Export all records to CSV."""
        if not self.records:
            raise ValueError("No records to export")
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        fieldnames = list(self.records[0].to_dict().keys())
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in self.records:
                writer.writerow(record.to_dict())

    @staticmethod
    def load_csv(filepath: Path) -> list:
        """Load records from CSV."""
        records = []
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(TaskRecord.from_dict(row))
        return records


class SystemSummary:
    """Summary statistics for a single system."""

    def __init__(self, system_name: str, records: list):
        self.system_name = system_name
        self.records = records
        self.n_records = len(records)

        # Extract metrics vectors
        self.latencies = np.array([r.total_latency_ms for r in records])
        self.energies = np.array([r.total_energy_j for r in records])
        self.feasible = np.array([1.0 if r.deadline_met else 0.0 for r in records])

        # Handoff records
        handoff_records = [r for r in records if r.handoff_occurred]
        if handoff_records:
            self.handoff_success = np.array([1.0 if r.handoff_success else 0.0
                                            for r in handoff_records])
        else:
            self.handoff_success = np.array([])

    def compute_metrics(self):
        """Compute all summary metrics with bootstrap CI."""
        from .formulas import bootstrap_ci

        return {
            'n_records': self.n_records,
            'avg_latency_ms': bootstrap_ci(self.latencies),
            'p95_latency_ms': float(np.percentile(self.latencies, 95)),
            'feasibility_pct': bootstrap_ci(self.feasible * 100),
            'avg_energy_j': bootstrap_ci(self.energies),
            'handoff_success_pct': (
                bootstrap_ci(self.handoff_success * 100)
                if len(self.handoff_success) > 0 else (None, None, None)
            ),
        }

    def to_dict(self):
        """Convert summary to dictionary."""
        metrics = self.compute_metrics()
        return {
            'system': self.system_name,
            'n_records': metrics['n_records'],
            'avg_latency_ms_mean': metrics['avg_latency_ms'][0],
            'avg_latency_ms_ci_lower': metrics['avg_latency_ms'][1],
            'avg_latency_ms_ci_upper': metrics['avg_latency_ms'][2],
            'p95_latency_ms': metrics['p95_latency_ms'],
            'feasibility_pct_mean': metrics['feasibility_pct'][0],
            'feasibility_pct_ci_lower': metrics['feasibility_pct'][1],
            'feasibility_pct_ci_upper': metrics['feasibility_pct'][2],
            'avg_energy_j_mean': metrics['avg_energy_j'][0],
            'avg_energy_j_ci_lower': metrics['avg_energy_j'][1],
            'avg_energy_j_ci_upper': metrics['avg_energy_j'][2],
            'handoff_success_pct_mean': (
                metrics['handoff_success_pct'][0]
                if metrics['handoff_success_pct'][0] is not None else None
            ),
        }
