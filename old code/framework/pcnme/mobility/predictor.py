from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class TexitResult:
    t_exit_s: float
    in_coverage: bool


def compute_t_exit(
    *,
    vehicle_pos: Tuple[float, float],
    vehicle_speed_ms: float,
    vehicle_heading_deg: float,
    fog_pos: Tuple[float, float],
    fog_radius_m: float,
) -> TexitResult:
    """Compute time until vehicle exits a circular fog coverage zone."""
    dx = fog_pos[0] - vehicle_pos[0]
    dy = fog_pos[1] - vehicle_pos[1]
    dist = math.sqrt(dx * dx + dy * dy)
    if dist >= fog_radius_m:
        return TexitResult(t_exit_s=0.0, in_coverage=False)

    heading_rad = math.radians(vehicle_heading_deg)
    vx = float(vehicle_speed_ms) * math.cos(heading_rad)
    vy = float(vehicle_speed_ms) * math.sin(heading_rad)

    if dist < 1e-9:
        return TexitResult(t_exit_s=float("inf"), in_coverage=True)

    radial_x, radial_y = -dx / dist, -dy / dist
    v_closing = vx * radial_x + vy * radial_y
    if v_closing <= 0:
        return TexitResult(t_exit_s=float("inf"), in_coverage=True)

    return TexitResult(t_exit_s=(fog_radius_m - dist) / v_closing, in_coverage=True)
