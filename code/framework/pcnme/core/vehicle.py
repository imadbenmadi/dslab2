from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class SpatialTag:
    x: float
    y: float
    speed_kmh: float
    heading_deg: float
    lat: Optional[float] = None
    lon: Optional[float] = None


@dataclass(frozen=True)
class TracePoint:
    timestamp_s: float
    lat: float
    lon: float
    speed_kmh: float
    heading_deg: float


class MobilityTrace:
    """Time-indexed mobility traces per vehicle."""

    def __init__(self, points_by_vehicle: Dict[str, List[TracePoint]]):
        self._points = {vid: sorted(points, key=lambda p: p.timestamp_s) for vid, points in points_by_vehicle.items()}

    def vehicle_ids(self) -> Iterable[str]:
        return self._points.keys()

    def get_nearest_point(self, vehicle_id: str, timestamp_s: float) -> Optional[TracePoint]:
        points = self._points.get(vehicle_id)
        if not points:
            return None
        # Linear scan is fine for Phase 1; can be replaced by bisect later.
        nearest = min(points, key=lambda p: abs(p.timestamp_s - timestamp_s))
        return nearest
