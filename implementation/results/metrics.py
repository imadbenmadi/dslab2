import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List

@dataclass
class SimMetrics:
    system_name: str
    task_latencies_ms: List[float] = field(default_factory=list)
    task_energies_j:   List[float] = field(default_factory=list)
    deadlines_met:     List[bool]  = field(default_factory=list)
    handoff_successes: List[bool]  = field(default_factory=list)
    fog_utilisation:   List[float] = field(default_factory=list)
    sdn_preinstall_hits: List[bool]= field(default_factory=list)
    boulder_rates:     List[float] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            'system': self.system_name,
            'avg_latency_ms':       np.mean(self.task_latencies_ms) if self.task_latencies_ms else 0,
            'p95_latency_ms':       np.percentile(self.task_latencies_ms, 95) if self.task_latencies_ms else 0,
            'avg_energy_j':         np.mean(self.task_energies_j) if self.task_energies_j else 0,
            'total_energy_j':       np.sum(self.task_energies_j) if self.task_energies_j else 0,
            'feasibility_rate':     np.mean(self.deadlines_met) if self.deadlines_met else 0,
            'handoff_success_rate': np.mean(self.handoff_successes) if self.handoff_successes else None,
            'avg_fog_utilisation':  np.mean(self.fog_utilisation) if self.fog_utilisation else 0,
            'sdn_hit_rate':         np.mean(self.sdn_preinstall_hits) if self.sdn_preinstall_hits else None,
            'avg_boulder_rate':     np.mean(self.boulder_rates) if self.boulder_rates else 0,
            'n_tasks':              len(self.task_latencies_ms),
        }

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([self.summary()])
