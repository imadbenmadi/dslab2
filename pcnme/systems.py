"""
Six task scheduling systems for comparison.
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Optional

from .constants import FOG_NODES, EC_THRESHOLD, FOG_MIPS
from .formulas import compute_ec, classify_step
from .dqn_agent import DQNAgent, DQNNetwork
from .simulation import TaskExecutor, SimulationEnvironment


class BaseSystem(ABC, TaskExecutor):
    """Abstract base class for all systems."""

    def __init__(self, env: SimulationEnvironment, seed: int = 42):
        super().__init__(env)
        self.env = env
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.decisions = []

    def select_destination(self, vehicle_id: str, step_id: int, step_MI: int,
                          sim_time_s: float) -> str:
        """Select destination for pebble steps; boulders always go to cloud."""
        if classify_step(step_MI) == "boulder":
            return "cloud"
        return self._select_pebble_destination(vehicle_id, step_id, step_MI, sim_time_s)

    @abstractmethod
    def _select_pebble_destination(self, vehicle_id: str, step_id: int,
                                   step_MI: int, sim_time_s: float) -> str:
        """Select fog node for pebble steps."""
        pass

    def record_decision(self, vehicle_id: str, step_id: int, destination: str) -> None:
        """Record a scheduling decision."""
        self.decisions.append({
            "vehicle_id": vehicle_id,
            "step_id": step_id,
            "destination": destination,
        })


class RandomSystem(BaseSystem):
    """Random fog assignment for pebbles."""

    def _select_pebble_destination(self, vehicle_id: str, step_id: int,
                                   step_MI: int, sim_time_s: float) -> str:
        """Choose random fog node."""
        return self.rng.choice(list(self.env.fog_nodes.keys()))


class GreedySystem(BaseSystem):
    """Least-loaded fog node for pebbles."""

    def _select_pebble_destination(self, vehicle_id: str, step_id: int,
                                   step_MI: int, sim_time_s: float) -> str:
        """Choose least-loaded fog node."""
        fog_state = self.env.get_fog_state()
        loads = {name: info["load"] for name, info in fog_state.items()}
        return min(loads, key=loads.get)


class NSGA2StaticSystem(BaseSystem):
    """Offline NSGA-II optimization with static routing table."""

    def __init__(self, env: SimulationEnvironment, routing_table: Optional[Dict] = None,
                 seed: int = 42):
        super().__init__(env, seed)
        # For simplicity, use greedy as fallback if no routing table
        self.routing_table = routing_table or {}

    def _select_pebble_destination(self, vehicle_id: str, step_id: int,
                                   step_MI: int, sim_time_s: float) -> str:
        """Look up pre-computed assignment."""
        key = (step_id, int(sim_time_s) % 10)  # bucketing
        if key in self.routing_table:
            return self.routing_table[key]
        # Fallback to greedy
        fog_state = self.env.get_fog_state()
        loads = {name: info["load"] for name, info in fog_state.items()}
        return min(loads, key=loads.get)


class DQNColdStartSystem(BaseSystem):
    """DQN from random initialization (no BC pre-training)."""

    def __init__(self, env: SimulationEnvironment, seed: int = 42):
        super().__init__(env, seed)
        self.agent = DQNAgent()
        # Initialize with Xavier uniform instead of defaults
        for p in self.agent.online_net.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)

    def _select_pebble_destination(self, vehicle_id: str, step_id: int,
                                   step_MI: int, sim_time_s: float) -> str:
        """Use DQN to select destination."""
        # Build state (simplified)
        fog_state = self.env.get_fog_state()
        fog_loads = {name: info["load"] for name, info in fog_state.items()}
        fog_queues = {name: info["queue"] for name, info in fog_state.items()}
        speed = self.env.vehicles[vehicle_id].get_speed_at_time(sim_time_s)
        t_exit = self.env.compute_t_exit_to_fog(vehicle_id, "A", sim_time_s)

        from .formulas import build_state
        state = build_state(fog_loads, fog_queues, step_MI, 0.5, speed, t_exit, 100.0)

        action = self.agent.select_action(state, training=True)
        actions_map = ["A", "B", "C", "D", "cloud"]
        return actions_map[action]


class DQNBCOnlySystem(BaseSystem):
    """DQN pre-trained with BC but frozen weights (no online updates)."""

    def __init__(self, env: SimulationEnvironment, weights_path=None, seed: int = 42):
        super().__init__(env, seed)
        self.agent = DQNAgent()
        if weights_path:
            self.agent.load_weights(weights_path)
        # Freeze weights
        for param in self.agent.online_net.parameters():
            param.requires_grad = False

    def _select_pebble_destination(self, vehicle_id: str, step_id: int,
                                   step_MI: int, sim_time_s: float) -> str:
        """Use pre-trained DQN (frozen)."""
        fog_state = self.env.get_fog_state()
        fog_loads = {name: info["load"] for name, info in fog_state.items()}
        fog_queues = {name: info["queue"] for name, info in fog_state.items()}
        speed = self.env.vehicles[vehicle_id].get_speed_at_time(sim_time_s)
        t_exit = self.env.compute_t_exit_to_fog(vehicle_id, "A", sim_time_s)

        from .formulas import build_state
        state = build_state(fog_loads, fog_queues, step_MI, 0.5, speed, t_exit, 100.0)

        action = self.agent.select_action(state, training=False)
        actions_map = ["A", "B", "C", "D", "cloud"]
        return actions_map[action]


class ProposedSystem(BaseSystem):
    """Full PCNME with DQN, behavioral cloning, and online learning."""

    def __init__(self, env: SimulationEnvironment, weights_path=None, seed: int = 42):
        super().__init__(env, seed)
        self.agent = DQNAgent()
        if weights_path:
            self.agent.load_weights(weights_path)

    def _select_pebble_destination(self, vehicle_id: str, step_id: int,
                                   step_MI: int, sim_time_s: float) -> str:
        """Use DQN with proactive handoff logic."""
        fog_state = self.env.get_fog_state()
        fog_loads = {name: info["load"] for name, info in fog_state.items()}
        fog_queues = {name: info["queue"] for name, info in fog_state.items()}
        speed = self.env.vehicles[vehicle_id].get_speed_at_time(sim_time_s)
        t_exit = self.env.compute_t_exit_to_fog(vehicle_id, "A", sim_time_s)

        from .formulas import build_state
        state = build_state(fog_loads, fog_queues, step_MI, 0.5, speed, t_exit, 100.0)

        action = self.agent.select_action(state, training=True)
        actions_map = ["A", "B", "C", "D", "cloud"]
        return actions_map[action]


def create_system(system_type: str, env: SimulationEnvironment, 
                 weights_path=None, routing_table=None,
                 seed: int = 42) -> BaseSystem:
    """Factory function for system creation."""
    if system_type == "random":
        return RandomSystem(env, seed)
    elif system_type == "greedy":
        return GreedySystem(env, seed)
    elif system_type == "nsga2_static":
        return NSGA2StaticSystem(env, routing_table, seed)
    elif system_type == "dqn_cold":
        return DQNColdStartSystem(env, seed)
    elif system_type == "dqn_bc_only":
        return DQNBCOnlySystem(env, weights_path, seed)
    elif system_type == "proposed":
        return ProposedSystem(env, weights_path, seed)
    else:
        raise ValueError(f"Unknown system type: {system_type}")


# Fix for nn import
import torch.nn as nn
