"""SDN controller with policy-driven routing behavior for task offloading."""

from typing import Dict, List
from dataclasses import dataclass
import random

@dataclass
class FlowRule:
    """OpenFlow routing rule."""
    flow_id: str
    priority: int
    match_criteria: Dict
    actions: List[str]
    install_time: float = 0.0
    hit_count: int = 0


class SDNController:
    """OpenFlow-compatible SDN controller for task offloading routing."""
    
    def __init__(self):
        self.rules: Dict[str, FlowRule] = {}
        self.switch_stats: Dict[str, Dict] = {}
        self.active_flows: Dict[str, Dict] = {}
        self.preinstalled_count = 0
        self.reactive_count = 0
        self.preinstalled_hits = 0
        self.packet_drop_count = 0

        # Per-policy path profiles that Agent2 can optimize over.
        # action: 0 primary, 1 alt1, 2 alt2, 3 reserve_vip, 4 best_effort
        self.path_profiles = {
            0: {"name": "primary", "base_ms": 5.0, "jitter_ms": 1.5, "loss": 0.010, "hops": 2},
            1: {"name": "alt1", "base_ms": 7.0, "jitter_ms": 1.8, "loss": 0.007, "hops": 3},
            2: {"name": "alt2", "base_ms": 9.0, "jitter_ms": 2.0, "loss": 0.006, "hops": 4},
            3: {"name": "vip", "base_ms": 3.5, "jitter_ms": 0.8, "loss": 0.003, "hops": 2},
            4: {"name": "best_effort", "base_ms": 12.0, "jitter_ms": 3.5, "loss": 0.030, "hops": 2},
        }

    def _rule_key(self, switch_id: str, flow_id: str) -> str:
        return f"{switch_id}:{flow_id}"

    def _has_matching_rule(self, source: str, destination: str) -> bool:
        for rule in self.rules.values():
            src = str(rule.match_criteria.get("src", ""))
            dst = str(rule.match_criteria.get("dst", ""))
            if src == source and dst == destination:
                return True
        return False
    
    def install_rule(self, switch_id: str, rule: FlowRule, install_time: float = 0.0) -> bool:
        """
        Install a routing rule on a switch (proactive installation).
        
        Args:
            switch_id: OpenFlow switch identifier
            rule: FlowRule object with match criteria and actions
            install_time: Simulation timestamp
            
        Returns:
            True if successfully installed
        """
        try:
            rule.install_time = install_time
            rule_key = self._rule_key(switch_id, rule.flow_id)
            self.rules[rule_key] = rule
            self.preinstalled_count += 1
            return True
        except Exception as e:
            print(f"Error installing rule: {e}")
            return False
    
    def route_flow(self, flow_id: str, source: str, destination: str, 
                   path: List[str], overhead_ms: float = 0.0) -> Dict:
        """
        Route a flow along a specific path (reactive routing).
        
        Args:
            flow_id: Unique flow identifier
            source: Source node
            destination: Destination node
            path: List of nodes in the path [source, ..., destination]
            overhead_ms: SDN lookup/install overhead
            
        Returns:
            Dict with routing info {latency, hops, preinstalled}
        """
        try:
            preinstalled = self._has_matching_rule(source, destination)
            
            if preinstalled:
                self.preinstalled_hits += 1
                routing_latency = 0
            else:
                routing_latency = overhead_ms / 1000.0
                self.reactive_count += 1
            
            self.active_flows[flow_id] = {
                'source': source,
                'destination': destination,
                'path': path,
                'hops': len(path) - 1,
                'preinstalled': preinstalled,
                'routing_latency': routing_latency,
            }
            
            return {
                'flow_id': flow_id,
                'hops': len(path) - 1,
                'routing_latency_ms': routing_latency * 1000,
                'preinstalled': preinstalled,
                'path': path,
            }
        
        except Exception as e:
            print(f"Error routing flow {flow_id}: {e}")
            return {'error': str(e)}

    def route_by_policy(
        self,
        flow_id: str,
        source: str,
        destination: str,
        policy_action: int,
        sim_time: float,
        payload_kb: float = 50.0,
        queue_pressure: float = 0.3,
    ) -> Dict:
        """
        Route a task according to Agent2 action policy and network state.
        Returns detailed SDN/network outcome for reward shaping and observability.
        """
        profile = self.path_profiles.get(int(policy_action), self.path_profiles[0])
        q = max(0.0, min(1.0, float(queue_pressure)))

        preinstalled = self._has_matching_rule(source, destination)
        if preinstalled:
            self.preinstalled_hits += 1
            ctrl_overhead_ms = 0.0
        else:
            ctrl_overhead_ms = random.uniform(8.0, 15.0) * (1.0 + 0.6 * q)
            self.reactive_count += 1

        hops = int(profile["hops"])
        if destination == "CLOUD":
            hops += 1

        propagation_ms = float(profile["base_ms"] + random.uniform(0.0, profile["jitter_ms"]))
        queue_ms = (3.0 + 10.0 * q) * (0.7 if int(policy_action) == 3 else 1.0)
        size_ms = min(max(payload_kb, 1.0) / 180.0, 8.0)
        hop_ms = hops * 0.9
        path_delay_ms = propagation_ms + queue_ms + size_ms + hop_ms

        drop_prob = float(profile["loss"] * (1.0 + 0.8 * q))
        packet_drop = random.random() < drop_prob
        retry_penalty_ms = random.uniform(10.0, 22.0) if packet_drop else 0.0
        if packet_drop:
            self.packet_drop_count += 1

        total_delay_ms = path_delay_ms + ctrl_overhead_ms + retry_penalty_ms

        if destination == "CLOUD":
            path = [source, "sw-core", "metro-gw", "CLOUD"]
        else:
            path = [source, "sw-core", destination]

        self.active_flows[flow_id] = {
            "source": source,
            "destination": destination,
            "path": path,
            "hops": hops,
            "policy_action": int(policy_action),
            "policy_name": profile["name"],
            "preinstalled": preinstalled,
            "packet_drop": packet_drop,
            "ctrl_overhead_ms": float(ctrl_overhead_ms),
            "path_delay_ms": float(path_delay_ms),
            "total_delay_ms": float(total_delay_ms),
            "sim_time": float(sim_time),
        }

        return {
            "flow_id": flow_id,
            "source": source,
            "destination": destination,
            "policy_action": int(policy_action),
            "policy_name": profile["name"],
            "path": path,
            "hops": hops,
            "preinstalled": preinstalled,
            "packet_drop": packet_drop,
            "ctrl_overhead_ms": float(ctrl_overhead_ms),
            "path_delay_ms": float(path_delay_ms),
            "total_delay_ms": float(total_delay_ms),
        }
    
    def query_switch(self, switch_id: str) -> Dict:
        """
        Query switch statistics and current state.
        
        Args:
            switch_id: OpenFlow switch identifier
            
        Returns:
            Dict with switch statistics
        """
        try:
            switch_rules = [r for rkey, r in self.rules.items() if rkey.startswith(switch_id)]
            total_hits = sum(r.hit_count for r in switch_rules)
            
            return {
                'switch_id': switch_id,
                'active_rules': len(switch_rules),
                'total_hits': total_hits,
                'preinstalled_hits': self.preinstalled_hits,
                'reactive_rules': self.reactive_count,
                'active_flows': len(self.active_flows),
            }
        
        except Exception as e:
            print(f"Error querying switch {switch_id}: {e}")
            return {'error': str(e)}
    
    def get_preinstall_efficiency(self) -> float:
        """Calculate efficiency of pre-installed rules."""
        total_rules = self.preinstalled_count + self.reactive_count
        if total_rules == 0:
            return 0.0
        return (self.preinstalled_count / total_rules) * 100
    
    def get_status(self) -> Dict:
        """Get overall controller status."""
        active = list(self.active_flows.values())
        avg_total_delay = 0.0
        if active:
            avg_total_delay = sum(f.get("total_delay_ms", 0.0) for f in active) / len(active)

        return {
            'total_rules': len(self.rules),
            'active_flows': len(self.active_flows),
            'preinstalled_count': self.preinstalled_count,
            'preinstalled_hits': self.preinstalled_hits,
            'reactive_count': self.reactive_count,
            'packet_drop_count': self.packet_drop_count,
            'avg_total_delay_ms': avg_total_delay,
            'preinstall_efficiency_pct': self.get_preinstall_efficiency(),
        }
