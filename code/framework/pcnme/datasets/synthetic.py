from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from pcnme.core.config import Settings
from pcnme.core.topology import Topology
from pcnme.optimizer.problem import OffloadingUnit


class SyntheticGenerator:
    """Synthetic generators for mobility and pebble-task batches."""

    def __init__(self, *, settings: Settings, topology: Topology, rng: np.random.Generator):
        self.settings = settings
        self.topology = topology
        self.rng = rng

    def sample_fog_loads(self) -> Dict[str, float]:
        loads: Dict[str, float] = {}
        for fog in self.topology.iter_fogs():
            loads[fog.id] = float(np.clip(fog.initial_load + self.rng.uniform(-0.12, 0.12), 0.05, 0.95))
        return loads

    def generate_pebble_units(self, *, batch_size: int, batch_index: int) -> List[OffloadingUnit]:
        # Generate MI below the pebble threshold (EC < threshold).
        max_pebble_mi = float(self.settings.EC_THRESHOLD) * float(self.settings.FOG_MIPS) * 0.98
        min_mi = 50.0

        units: List[OffloadingUnit] = []
        for i in range(int(batch_size)):
            mi = float(self.rng.uniform(min_mi, max_pebble_mi))
            in_kb = float(self.rng.uniform(5.0, 200.0))
            out_kb = float(self.rng.uniform(1.0, 80.0))

            # Place vehicles near some fog so feasibility exists.
            fog = self.rng.choice(list(self.topology.iter_fogs()))
            angle = float(self.rng.uniform(0.0, 2.0 * np.pi))
            radius = float(self.rng.uniform(0.0, self.settings.FOG_COVERAGE_RADIUS * 0.95))
            vx = float(fog.pos.x + radius * np.cos(angle))
            vy = float(fog.pos.y + radius * np.sin(angle))

            units.append(
                OffloadingUnit(
                    unit_id=f"B{batch_index:04d}-U{i:04d}",
                    mi=mi,
                    in_kb=in_kb,
                    out_kb=out_kb,
                    vehicle_xy=(vx, vy),
                    ingress_fog_id=fog.id,
                    deadline_ms=float(self.rng.uniform(50.0, 200.0)),
                )
            )

        return units
