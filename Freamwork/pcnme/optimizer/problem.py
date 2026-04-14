from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np
from pymoo.core.problem import Problem

from pcnme.core.topology import Topology
from pcnme.core.config import Settings


@dataclass(frozen=True)
class OffloadingUnit:
    unit_id: str
    mi: float
    in_kb: float
    out_kb: float
    vehicle_xy: Tuple[float, float]
    ingress_fog_id: Optional[str] = None
    deadline_ms: Optional[float] = None


class TaskOffloadingProblem(Problem):
    """Multi-objective placement problem: minimize latency and energy."""

    def __init__(
        self,
        *,
        settings: Settings,
        topology: Topology,
        units: Sequence[OffloadingUnit],
        fog_loads: Optional[dict[str, float]] = None,
    ):
        self.settings = settings
        self.topology = topology
        self.units = list(units)
        self.actions = topology.fog_ids() + ["CLOUD"]
        self.n_actions = len(self.actions)
        self.fog_loads = fog_loads or {f.id: f.initial_load for f in topology.iter_fogs()}

        super().__init__(
            n_var=len(self.units),
            n_obj=2,
            xl=0,
            xu=self.n_actions - 1,
            elementwise_evaluation=False,
        )

    def _evaluate(self, X, out, *args, **kwargs):
        # Ensure integer actions
        X = np.clip(np.rint(X), self.xl, self.xu).astype(int)

        latency = np.zeros(X.shape[0], dtype=float)
        energy = np.zeros(X.shape[0], dtype=float)

        for j, unit in enumerate(self.units):
            targets = np.take(self.actions, X[:, j])
            unit_lat, unit_energy = self._unit_costs(unit, targets)
            latency += unit_lat
            energy += unit_energy

        out["F"] = np.column_stack([latency, energy])

    def _unit_costs(self, unit: OffloadingUnit, targets: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        # Vectorized computation per candidate solution
        in_kb = float(unit.in_kb)
        mi = float(unit.mi)

        # Upload time in ms (vehicle->ingress)
        tx_ms = (in_kb * 8.0) / (self.settings.BANDWIDTH_MBPS * 1000.0) * 1000.0
        access_ms = float(self.settings.G5_LATENCY_MS) + float(tx_ms)

        # Determine ingress fog if not explicitly provided.
        ingress_id = unit.ingress_fog_id
        if ingress_id is None:
            ingress_id, _ = self.topology.nearest_fog_in_range(unit.vehicle_xy[0], unit.vehicle_xy[1])
        else:
            # If an ingress fog is provided but the vehicle is out of range, treat as disconnected.
            try:
                ingress_fog = self.topology.get_fog(str(ingress_id))
                dist = self.topology.distance_m(unit.vehicle_xy, (ingress_fog.pos.x, ingress_fog.pos.y))
                if dist > self.topology.fog_coverage_radius_m:
                    ingress_id = None
            except KeyError:
                ingress_id = None

        fog_fog_latency_ms = max(2.0, float(self.settings.WAN_LATENCY_MS) * 0.30)
        fog_cloud_latency_ms = float(self.settings.WAN_LATENCY_MS)

        lat = np.zeros(len(targets), dtype=float)
        eng = np.zeros(len(targets), dtype=float)

        for idx, target in enumerate(targets):
            if target == "CLOUD":
                # Cloud execution: allow direct-to-cloud if no ingress fog.
                compute_s = mi / float(self.settings.CLOUD_MIPS)
                backhaul_ms = (in_kb * 8.0) / (self.settings.FOG_CLOUD_BW * 1000.0) * 1000.0
                net_ms = access_ms + fog_cloud_latency_ms + backhaul_ms
                lat[idx] = net_ms + compute_s * 1000.0
                # Energy model: cloud is generally more energy-expensive (infra + long-haul).
                eng[idx] = (in_kb / 1024.0) * 0.020 + compute_s * 0.050 + 0.010
            else:
                fog = self.topology.get_fog(str(target))
                load = float(np.clip(self.fog_loads.get(fog.id, fog.initial_load), 0.05, 0.95))
                eff_mips = float(fog.mips) * max(1.0 - load, 0.05)
                compute_s = mi / eff_mips

                if ingress_id is None:
                    # Vehicle is not connected to any fog: cannot execute on fog nodes.
                    lat[idx] = 1e6
                    eng[idx] = 1e3
                    continue

                # Vehicle uploads to ingress fog; ingress forwards to target fog if different.
                if str(target) == str(ingress_id):
                    forward_ms = 0.0
                    forward_energy = 0.0
                else:
                    forward_ms = fog_fog_latency_ms + (in_kb * 8.0) / (self.settings.FOG_FOG_BW * 1000.0) * 1000.0
                    forward_energy = (in_kb / 1024.0) * 0.004

                lat[idx] = access_ms + forward_ms + compute_s * 1000.0
                eng[idx] = (in_kb / 1024.0) * 0.010 + forward_energy + compute_s * 0.020

        return lat, eng
