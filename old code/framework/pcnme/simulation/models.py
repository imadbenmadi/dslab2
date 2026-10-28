from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class VehicleState:
    id: str
    x: float
    y: float
    speed_ms: float
    heading_deg: float
    connected_fog_id: Optional[str] = None


@dataclass
class FogRuntimeState:
    id: str
    x: float
    y: float
    load: float
    queue_depth: int


@dataclass
class MetricsSummary:
    tasks_total: int = 0
    tasks_cloud: int = 0
    tasks_fog: int = 0
    packet_drops: int = 0
    avg_latency_ms: float = 0.0
    avg_energy: float = 0.0

    def update(self, *, latency_ms: float, energy: float, to_cloud: bool, packet_drop: bool) -> None:
        self.tasks_total += 1
        if to_cloud:
            self.tasks_cloud += 1
        else:
            self.tasks_fog += 1
        if packet_drop:
            self.packet_drops += 1
        # online mean
        n = float(self.tasks_total)
        self.avg_latency_ms += (float(latency_ms) - self.avg_latency_ms) / n
        self.avg_energy += (float(energy) - self.avg_energy) / n


@dataclass
class SimulationSnapshot:
    sim_time_s: float
    vehicles: List[VehicleState] = field(default_factory=list)
    fogs: List[FogRuntimeState] = field(default_factory=list)
    metrics: MetricsSummary = field(default_factory=MetricsSummary)

    def to_dict(self) -> Dict:
        return {
            "sim_time_s": float(self.sim_time_s),
            "vehicles": [vars(v) for v in self.vehicles],
            "fogs": [vars(f) for f in self.fogs],
            "metrics": vars(self.metrics),
        }
