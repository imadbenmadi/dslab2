"""
OpenFlow v1.3 Control Plane Integration.
Manages real or simulated switches with flow rules, metrics, and dynamic routing.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

# Note: For real deployment, install: pip install ryu
# from ryu.base import app_manager
# from ryu.controller.ofp_event import EventOFPSwitchFeatures
# from ryu.controller import ofp_event
# from ryu.lib.packet import packet, ethernet, ipv4, tcp


class MatchFieldType(Enum):
    """OpenFlow match fields."""
    IN_PORT = "in_port"
    ETH_DST = "eth_dst"
    ETH_SRC = "eth_src"
    ETH_TYPE = "eth_type"
    IPV4_SRC = "ipv4_src"
    IPV4_DST = "ipv4_dst"
    TCP_SRC = "tcp_src"
    TCP_DST = "tcp_dst"


class ActionType(Enum):
    """OpenFlow actions."""
    OUTPUT = "output"
    DROP = "drop"
    SET_FIELD = "set_field"
    PUSH_VLAN = "push_vlan"
    POP_VLAN = "pop_vlan"
    GOTO_TABLE = "goto_table"


@dataclass
class MatchField:
    """OpenFlow match criterion."""
    field_type: MatchFieldType
    value: str


@dataclass
class Action:
    """OpenFlow action."""
    action_type: ActionType
    params: Dict = None

    def __post_init__(self):
        if self.params is None:
            self.params = {}


@dataclass
class FlowRule:
    """OpenFlow flow rule."""
    priority: int
    matches: List[MatchField]
    actions: List[Action]
    idle_timeout: int = 60
    hard_timeout: int = 3600
    table_id: int = 0
    cookie: int = 0


@dataclass
class SwitchPort:
    """Switch port state and metrics."""
    port_id: int
    name: str
    enabled: bool = True
    rx_packets: int = 0
    rx_bytes: int = 0
    tx_packets: int = 0
    tx_bytes: int = 0
    rx_dropped: int = 0
    tx_dropped: int = 0


@dataclass
class SwitchMetrics:
    """Switch performance metrics."""
    datapath_id: str
    timestamp: float
    ports: Dict[int, SwitchPort]
    active_flows: int = 0
    table_lookups: int = 0
    matched_packets: int = 0
    missed_packets: int = 0


class OpenFlowSwitch:
    """
    Represents an OpenFlow switch.
    Can be backed by OVS (Open vSwitch) or simulated.
    """

    def __init__(self, datapath_id: str, name: str, num_ports: int = 8):
        self.datapath_id = datapath_id
        self.name = name
        self.num_ports = num_ports

        # Flow tables (table_id -> list of flows)
        self.flow_tables: Dict[int, List[FlowRule]] = defaultdict(list)

        # Ports
        self.ports: Dict[int, SwitchPort] = {
            i: SwitchPort(port_id=i, name=f"port-{i}")
            for i in range(1, num_ports + 1)
        }

        # Metrics
        self.metrics = SwitchMetrics(
            datapath_id=datapath_id,
            timestamp=time.time(),
            ports=self.ports
        )

        print(f"[OFP] Switch initialized: {name} ({datapath_id}) with {num_ports} ports")

    def install_flow_rule(self, table_id: int, rule: FlowRule) -> bool:
        """Install flow rule on switch."""
        if table_id not in self.flow_tables:
            self.flow_tables[table_id] = []

        # Sort by priority (higher first)
        self.flow_tables[table_id].append(rule)
        self.flow_tables[table_id].sort(key=lambda x: x.priority, reverse=True)

        print(f"[OFP] Flow installed on {self.name} table {table_id}: "
              f"priority={rule.priority}, matches={len(rule.matches)}, "
              f"actions={len(rule.actions)}")
        return True

    def delete_flow_rule(self, table_id: int, cookie: int) -> bool:
        """Delete flow rule by cookie."""
        if table_id in self.flow_tables:
            before = len(self.flow_tables[table_id])
            self.flow_tables[table_id] = [r for r in self.flow_tables[table_id] if r.cookie != cookie]
            deleted = before - len(self.flow_tables[table_id])
            if deleted > 0:
                print(f"[OFP] Deleted {deleted} flow(s) from {self.name} table {table_id}")
            return deleted > 0
        return False

    def match_packet(self, packet_data: Dict) -> Optional[List[Action]]:
        """
        Match packet against flow tables.
        Returns actions if matched, None otherwise.
        """
        # Default table
        table_id = 0
        for rule in self.flow_tables.get(table_id, []):
            if self._packet_matches_rule(packet_data, rule):
                self.metrics.matched_packets += 1
                return rule.actions

        # Packet missed
        self.metrics.missed_packets += 1
        return None

    def _packet_matches_rule(self, packet_data: Dict, rule: FlowRule) -> bool:
        """Check if packet matches all rule criteria."""
        for match in rule.matches:
            packet_val = packet_data.get(match.field_type.value)
            if packet_val != match.value:
                return False
        return True

    def get_metrics(self) -> SwitchMetrics:
        """Get current switch metrics."""
        self.metrics.timestamp = time.time()
        self.metrics.active_flows = sum(len(flows) for flows in self.flow_tables.values())
        return self.metrics

    def update_port_stats(self, port_id: int, rx_packets: int, tx_packets: int, rx_bytes: int, tx_bytes: int):
        """Update port statistics."""
        if port_id in self.ports:
            self.ports[port_id].rx_packets = rx_packets
            self.ports[port_id].tx_packets = tx_packets
            self.ports[port_id].rx_bytes = rx_bytes
            self.ports[port_id].tx_bytes = tx_bytes


class OpenFlowController:
    """
    OpenFlow SDN Controller.
    Manages switches, installs flows, monitors network state.
    """

    def __init__(self, controller_id: str = "smartcity-ofp-controller"):
        self.controller_id = controller_id
        self.switches: Dict[str, OpenFlowSwitch] = {}
        self.flow_stats: Dict[str, List[Dict]] = defaultdict(list)
        self.network_topology: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

        print(f"[OFP] Controller initialized: {controller_id}")

    def register_switch(self, datapath_id: str, name: str, num_ports: int = 8) -> OpenFlowSwitch:
        """Register a switch with the controller."""
        switch = OpenFlowSwitch(datapath_id, name, num_ports)
        self.switches[datapath_id] = switch
        print(f"[OFP] Switch registered: {datapath_id}")
        return switch

    def install_vehicle_to_fog_flows(self, vehicle_port: int, fog_id: str, fog_port: int):
        """
        Install flows for vehicle → fog routing.
        Used when vehicle decides to offload to fog.
        """
        for switch_id, switch in self.switches.items():
            if "vehicle" in switch_id.lower():
                # Match: vehicle traffic
                rule = FlowRule(
                    priority=100,
                    matches=[
                        MatchField(MatchFieldType.IN_PORT, str(vehicle_port)),
                    ],
                    actions=[
                        Action(ActionType.OUTPUT, {"port": fog_port}),
                    ],
                    cookie=hash(f"veh2fog-{vehicle_port}-{fog_id}") & 0xFFFFFFFF
                )
                switch.install_flow_rule(0, rule)

    def install_fog_to_cloud_flows(self, fog_id: str, fog_port: int, cloud_port: int):
        """
        Install flows for fog → cloud routing.
        Used when fog offloads to cloud (boulder).
        """
        for switch_id, switch in self.switches.items():
            if fog_id in switch_id.lower():
                rule = FlowRule(
                    priority=90,
                    matches=[
                        MatchField(MatchFieldType.IN_PORT, str(fog_port)),
                    ],
                    actions=[
                        Action(ActionType.OUTPUT, {"port": cloud_port}),
                    ],
                    cookie=hash(f"fog2cloud-{fog_id}-{cloud_port}") & 0xFFFFFFFF
                )
                switch.install_flow_rule(0, rule)

    def install_load_balancing_flows(self, ingress_port: int, egress_ports: List[int], weights: List[float]):
        """
        Install load-balancing flows using OpenFlow groups (if supported).
        Maps ingress to multiple egress ports with weights.
        """
        for switch_id, switch in self.switches.items():
            total_weight = sum(weights)
            for egress_port, weight in zip(egress_ports, weights):
                # Simple round-robin simulation
                probability = weight / total_weight
                rule = FlowRule(
                    priority=50,
                    matches=[
                        MatchField(MatchFieldType.IN_PORT, str(ingress_port)),
                    ],
                    actions=[
                        Action(ActionType.OUTPUT, {"port": egress_port, "probability": probability}),
                    ],
                    cookie=hash(f"lb-{ingress_port}-{egress_port}") & 0xFFFFFFFF
                )
                switch.install_flow_rule(0, rule)

    def install_qos_flows(self, ingress_port: int, vlan_id: int, priority_class: str = "high"):
        """
        Install QoS flows using VLAN tagging and priority.
        Used for latency-critical vs. best-effort traffic.
        """
        for switch_id, switch in self.switches.items():
            priority_value = 1000 if priority_class == "high" else 500

            rule = FlowRule(
                priority=priority_value,
                matches=[
                    MatchField(MatchFieldType.IN_PORT, str(ingress_port)),
                ],
                actions=[
                    Action(ActionType.PUSH_VLAN, {"vlan_id": vlan_id}),
                    Action(ActionType.OUTPUT, {"port": ingress_port + 1}),
                ],
                cookie=hash(f"qos-{ingress_port}-{priority_class}") & 0xFFFFFFFF
            )
            switch.install_flow_rule(0, rule)

    def get_network_statistics(self) -> Dict:
        """Get aggregate network statistics."""
        total_flows = 0
        total_rx_packets = 0
        total_tx_packets = 0

        for switch in self.switches.values():
            metrics = switch.get_metrics()
            total_flows += metrics.active_flows
            for port in metrics.ports.values():
                total_rx_packets += port.rx_packets
                total_tx_packets += port.tx_packets

        return {
            "timestamp": time.time(),
            "num_switches": len(self.switches),
            "total_active_flows": total_flows,
            "total_rx_packets": total_rx_packets,
            "total_tx_packets": total_tx_packets,
            "average_match_rate": self._calculate_match_rate(),
        }

    def _calculate_match_rate(self) -> float:
        """Calculate packet match rate across all switches."""
        total_matched = sum(s.metrics.matched_packets for s in self.switches.values())
        total_missed = sum(s.metrics.missed_packets for s in self.switches.values())
        total = total_matched + total_missed
        if total == 0:
            return 0.0
        return total_matched / total

    def export_flows_to_ovs_commands(self) -> str:
        """
        Export flow rules as Open vSwitch (ovs-ofctl) commands.
        Can be piped to ovs-ofctl to program real switches.
        """
        commands = []
        for switch_id, switch in self.switches.items():
            commands.append(f"# Flows for bridge {switch.name}")

            for table_id, rules in switch.flow_tables.items():
                for rule in rules:
                    match_str = ",".join([
                        f"{m.field_type.value}={m.value}"
                        for m in rule.matches
                    ])

                    action_str = ",".join([
                        f"{a.action_type.value}" if not a.params else
                        f"{a.action_type.value}({json.dumps(a.params)})"
                        for a in rule.actions
                    ])

                    cmd = f"ovs-ofctl add-flow {switch.name} " \
                          f"table={table_id},priority={rule.priority}," \
                          f"{match_str} actions={action_str}"
                    commands.append(cmd)

        return "\n".join(commands)


def bootstrap_openflow_controller() -> OpenFlowController:
    """
    Initialize OpenFlow controller with simulated switches.
    In production, would connect to real OVS or hardware switches via OpenFlow protocol.
    """
    controller = OpenFlowController()

    # Register simulated switches
    vehicle_sw = controller.register_switch("vehicle-br-001", name="br-vehicle", num_ports=4)
    fog_sw = controller.register_switch("fog-br-001", name="br-fog", num_ports=8)
    cloud_sw = controller.register_switch("cloud-br-001", name="br-cloud", num_ports=4)

    print(f"[OFP] Simulated network: vehicle-br → fog-br → cloud-br")

    return controller


# Production Integration Notes:
# ==========================
# To integrate with real Open vSwitch:
#
# 1. Install Ryu (OpenFlow framework):
#    pip install ryu
#
# 2. Configure OVS to connect to controller:
#    ovs-vsctl set-controller br-int tcp:<CONTROLLER_IP>:6633
#
# 3. Use Ryu app to listen for switch events:
#    from ryu.base import app_manager
#    from ryu.controller import ofp_event
#
# 4. Convert FlowRule objects to OpenFlow protocol messages
#
# 5. Handle switch events (HELLO, FEATURES_REPLY, PACKET_IN)
#
# See: https://ryu.readthedocs.io/ for full Ryu integration.
