from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from pcnme.core.config import Settings
from pcnme.core.topology import Topology
from pcnme.optimizer.problem import OffloadingUnit
from pcnme.utils.math import clip


def build_agent1_state(
    *,
    unit: OffloadingUnit,
    settings: Settings,
    topology: Topology,
    fog_loads: Dict[str, float],
) -> np.ndarray:
    """Construct the (13D) state vector for Agent1 (placement)."""
    # Normalisation constants (simple, stable defaults)
    mi_norm = clip(unit.mi / (settings.FOG_MIPS * settings.EC_THRESHOLD + 1e-9), 0.0, 2.0)
    in_norm = clip(unit.in_kb / 500.0, 0.0, 2.0)
    out_norm = clip(unit.out_kb / 200.0, 0.0, 2.0)
    dl_norm = clip((unit.deadline_ms or 0.0) / 200.0, 0.0, 5.0)

    loads = np.array([float(fog_loads.get(f.id, f.initial_load)) for f in topology.iter_fogs()], dtype=float)
    avg_load = float(loads.mean())
    min_load = float(loads.min())
    max_load = float(loads.max())

    ingress_id = unit.ingress_fog_id
    ingress_load = float(fog_loads.get(str(ingress_id), avg_load)) if ingress_id else avg_load

    if ingress_id:
        try:
            ingress = topology.get_fog(str(ingress_id))
            dist = topology.distance_m(unit.vehicle_xy, (ingress.pos.x, ingress.pos.y))
        except KeyError:
            dist = topology.fog_coverage_radius_m
    else:
        dist = topology.fog_coverage_radius_m
    dist_norm = clip(dist / max(topology.fog_coverage_radius_m, 1e-9), 0.0, 2.0)

    wan_norm = clip(settings.WAN_LATENCY_MS / 50.0, 0.0, 5.0)
    access_norm = clip(settings.G5_LATENCY_MS / 10.0, 0.0, 5.0)
    fogfog_norm = clip(settings.FOG_FOG_BW / 500.0, 0.0, 5.0)
    fogcloud_norm = clip(settings.FOG_CLOUD_BW / 2000.0, 0.0, 5.0)

    # Total: 13
    state = np.array(
        [
            mi_norm,
            in_norm,
            out_norm,
            dl_norm,
            ingress_load,
            avg_load,
            min_load,
            max_load,
            dist_norm,
            wan_norm,
            access_norm,
            fogfog_norm,
            fogcloud_norm,
        ],
        dtype=np.float32,
    )
    return state


def build_agent2_state(
    *,
    queue_pressure: float,
    payload_kb: float,
    destination_is_cloud: bool,
    preinstall_hit: bool,
    settings: Settings,
) -> np.ndarray:
    """Construct the (15D) state vector for Agent2 (SDN routing)."""
    q = clip(queue_pressure, 0.0, 1.0)
    size = clip(payload_kb / 500.0, 0.0, 5.0)
    dest = 1.0 if destination_is_cloud else 0.0
    hit = 1.0 if preinstall_hit else 0.0
    wan = clip(settings.WAN_LATENCY_MS / 50.0, 0.0, 5.0)
    reactive = clip(settings.SDN_REACTIVE_MS / 30.0, 0.0, 5.0)

    # Pad remaining features with simple interactions
    feats = [
        q,
        size,
        dest,
        hit,
        wan,
        reactive,
        q * size,
        q * wan,
        (1.0 - q) * (1.0 - size),
        size * dest,
        q * dest,
        hit * (1.0 - q),
        wan * dest,
        reactive * (1.0 - hit),
        1.0,
    ]
    return np.array(feats, dtype=np.float32)
