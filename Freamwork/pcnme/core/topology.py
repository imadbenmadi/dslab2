from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class Position:
    x: float
    y: float
    lat: Optional[float] = None
    lon: Optional[float] = None


@dataclass(frozen=True)
class FogNode:
    id: str
    name: str
    pos: Position
    mips: int
    initial_load: float = 0.3


@dataclass(frozen=True)
class CloudNode:
    name: str
    mips: int
    lat: Optional[float] = None
    lon: Optional[float] = None


@dataclass(frozen=True)
class NetworkLink:
    src: str
    dst: str
    bandwidth_mbps: float
    latency_ms: float


class Topology:
    """Topology definition for a fog-cloud environment."""

    def __init__(
        self,
        *,
        fog_nodes: List[FogNode],
        cloud: CloudNode,
        fog_coverage_radius_m: float,
    ):
        if not fog_nodes:
            raise ValueError("Topology requires at least one fog node")
        self.fog_nodes = list(fog_nodes)
        self.cloud = cloud
        self.fog_coverage_radius_m = float(fog_coverage_radius_m)
        self._fog_by_id: Dict[str, FogNode] = {f.id: f for f in fog_nodes}

    def fog_ids(self) -> List[str]:
        return [f.id for f in self.fog_nodes]

    def get_fog(self, fog_id: str) -> FogNode:
        return self._fog_by_id[fog_id]

    @staticmethod
    def distance_m(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return float(np.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2))

    def nearest_fog_in_range(self, x: float, y: float) -> Tuple[Optional[str], float]:
        best_id: Optional[str] = None
        best_dist = 1e18
        for fog in self.fog_nodes:
            dist = self.distance_m((x, y), (fog.pos.x, fog.pos.y))
            if dist <= self.fog_coverage_radius_m and dist < best_dist:
                best_dist = dist
                best_id = fog.id
        return best_id, float(best_dist)

    def iter_fogs(self) -> Iterable[FogNode]:
        return iter(self.fog_nodes)
