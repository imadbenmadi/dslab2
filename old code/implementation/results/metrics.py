import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict

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


def _bootstrap_ci(values: List[float], n_boot: int = 1000, alpha: float = 0.05) -> Dict[str, float]:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    if arr.size == 1:
        v = float(arr[0])
        return {"mean": v, "ci_low": v, "ci_high": v}

    rng = np.random.default_rng(42)
    means = []
    for _ in range(n_boot):
        sample = rng.choice(arr, size=arr.size, replace=True)
        means.append(float(np.mean(sample)))
    low = float(np.percentile(means, 100 * (alpha / 2)))
    high = float(np.percentile(means, 100 * (1 - alpha / 2)))
    return {"mean": float(np.mean(arr)), "ci_low": low, "ci_high": high}


def _cohen_d(a: List[float], b: List[float]) -> float:
    xa = np.asarray(a, dtype=float)
    xb = np.asarray(b, dtype=float)
    if xa.size < 2 or xb.size < 2:
        return 0.0
    pooled = np.sqrt(((xa.size - 1) * np.var(xa, ddof=1) + (xb.size - 1) * np.var(xb, ddof=1)) / (xa.size + xb.size - 2))
    if pooled <= 1e-12:
        return 0.0
    return float((np.mean(xa) - np.mean(xb)) / pooled)


def compare_systems(metrics: Dict[str, SimMetrics]) -> pd.DataFrame:
    """Create richer comparative statistics across systems."""
    rows = []
    names = list(metrics.keys())
    for name, m in metrics.items():
        lat_ci = _bootstrap_ci(m.task_latencies_ms)
        en_ci = _bootstrap_ci(m.task_energies_j)
        fea_ci = _bootstrap_ci([1.0 if x else 0.0 for x in m.deadlines_met])
        rows.append(
            {
                "system": name,
                "n_tasks": len(m.task_latencies_ms),
                "lat_mean": lat_ci["mean"],
                "lat_ci_low": lat_ci["ci_low"],
                "lat_ci_high": lat_ci["ci_high"],
                "energy_mean": en_ci["mean"],
                "energy_ci_low": en_ci["ci_low"],
                "energy_ci_high": en_ci["ci_high"],
                "feasibility_mean": fea_ci["mean"],
                "feasibility_ci_low": fea_ci["ci_low"],
                "feasibility_ci_high": fea_ci["ci_high"],
            }
        )

    # Pairwise effect sizes against proposed baseline if available.
    if "proposed" in metrics:
        ref = metrics["proposed"]
        for r in rows:
            other = metrics[r["system"]]
            r["effect_latency_vs_proposed"] = _cohen_d(other.task_latencies_ms, ref.task_latencies_ms)
            r["effect_energy_vs_proposed"] = _cohen_d(other.task_energies_j, ref.task_energies_j)

    return pd.DataFrame(rows)
