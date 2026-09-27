from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import random

from pcnme.core.config import Settings
from pcnme.sdn.rules import FlowRule, RuleCache


@dataclass(frozen=True)
class RouteResult:
    policy_action: int
    policy_name: str
    preinstall_hit: bool
    packet_drop: bool
    ctrl_overhead_ms: float
    total_delay_ms: float
    path: List[str]


class SDNController:
    """OpenFlow-like controller with reactive vs preinstalled overhead."""

    def __init__(self, *, settings: Settings):
        self.settings = settings
        self.cache = RuleCache()
        self.packet_drop_count = 0
        self.reactive_count = 0
        self.preinstall_hits = 0

        # action: 0 primary, 1 alt1, 2 alt2, 3 vip, 4 best_effort
        self.path_profiles = {
            0: {"name": "primary", "base_ms": 5.0, "jitter_ms": 1.5, "loss": 0.010, "hops": 2},
            1: {"name": "alt1", "base_ms": 7.0, "jitter_ms": 1.8, "loss": 0.007, "hops": 3},
            2: {"name": "alt2", "base_ms": 9.0, "jitter_ms": 2.0, "loss": 0.006, "hops": 4},
            3: {"name": "vip", "base_ms": 3.5, "jitter_ms": 0.8, "loss": 0.003, "hops": 2},
            4: {"name": "best_effort", "base_ms": 12.0, "jitter_ms": 3.5, "loss": 0.030, "hops": 2},
        }

    def install_rule(self, *, flow_id: str, src: str, dst: str, priority: int, sim_time_s: float) -> None:
        rule = FlowRule(
            flow_id=flow_id,
            src=src,
            dst=dst,
            priority=int(priority),
            actions=["forward"],
            installed_at_sim_s=float(sim_time_s),
        )
        self.cache.upsert(rule)

    def route_by_policy(
        self,
        *,
        flow_id: str,
        source: str,
        destination: str,
        policy_action: int,
        queue_pressure: float,
        payload_kb: float,
        sim_time_s: float,
    ) -> RouteResult:
        profile = self.path_profiles.get(int(policy_action), self.path_profiles[0])
        q = max(0.0, min(1.0, float(queue_pressure)))

        preinstall_hit = self.cache.has(src=source, dst=destination)
        if preinstall_hit:
            self.preinstall_hits += 1
            ctrl_overhead_ms = float(self.settings.SDN_PREINSTALL_MS)
        else:
            self.reactive_count += 1
            ctrl_overhead_ms = float(random.uniform(8.0, 15.0)) * (1.0 + 0.6 * q)
            # Install a rule after a reactive miss (simplified), so future flows may hit.
            self.install_rule(flow_id=flow_id, src=source, dst=destination, priority=1, sim_time_s=sim_time_s)

        hops = int(profile["hops"]) + (1 if destination == "CLOUD" else 0)
        propagation_ms = float(profile["base_ms"] + random.uniform(0.0, float(profile["jitter_ms"])))
        queue_ms = (3.0 + 10.0 * q) * (0.7 if int(policy_action) == 3 else 1.0)
        size_ms = min(max(float(payload_kb), 1.0) / 180.0, 8.0)
        hop_ms = hops * 0.9

        path_delay_ms = propagation_ms + queue_ms + size_ms + hop_ms
        drop_prob = float(profile["loss"] * (1.0 + 0.8 * q))
        packet_drop = random.random() < drop_prob
        if packet_drop:
            self.packet_drop_count += 1

        retry_penalty_ms = float(random.uniform(10.0, 22.0)) if packet_drop else 0.0
        total_delay_ms = path_delay_ms + ctrl_overhead_ms + retry_penalty_ms

        if destination == "CLOUD":
            path = [source, "sw-core", "metro-gw", "CLOUD"]
        else:
            path = [source, "sw-core", destination]

        return RouteResult(
            policy_action=int(policy_action),
            policy_name=str(profile["name"]),
            preinstall_hit=bool(preinstall_hit),
            packet_drop=bool(packet_drop),
            ctrl_overhead_ms=float(ctrl_overhead_ms),
            total_delay_ms=float(total_delay_ms),
            path=path,
        )
