"""
Simulation engine: FogNode, Vehicle, SimulationEnvironment.
"""

import numpy as np
from collections import deque
from typing import Dict, Optional, Tuple

from .constants import FOG_NODES, FOG_RADIUS
from .formulas import (
    t_exec_fog, t_exec_cloud, t_tx_fog, t_tx_cloud,
    compute_t_exit, compute_ec, step_energy
)


class FogNode:
    """Fog computing node with queue and CPU load model."""

    def __init__(self, name: str, pos: Tuple[float, float], initial_load: float):
        self.name = name
        self.pos = pos
        self.cpu_load = initial_load
        self.queue = deque()
        self.task_in_service = None
        self.time_remaining = 0.0

    def queue_task(self, task_id: str, service_time_ms: float) -> None:
        """Queue a task for execution."""
        self.queue.append((task_id, service_time_ms))

    def update(self, dt_s: float = 1.0) -> Optional[str]:
        """
        Execute tasks for dt_s seconds.
        Returns task_id if a task completes, None otherwise.
        """
        dt_ms = dt_s * 1000.0

        if self.task_in_service is None:
            if self.queue:
                self.task_in_service, self.time_remaining = self.queue.popleft()
            else:
                self.cpu_load = max(0.0, self.cpu_load - 0.01)
                return None

        self.time_remaining -= dt_ms
        if self.time_remaining <= 0:
            completed = self.task_in_service
            self.task_in_service = None
            self.time_remaining = 0.0
            self.cpu_load = max(0.0, self.cpu_load - 0.02)
            return completed

        return None

    def get_load(self) -> float:
        """Return current CPU load."""
        return min(0.99, self.cpu_load)

    def get_queue_length(self) -> int:
        """Return queue length."""
        return len(self.queue) + (1 if self.task_in_service else 0)


class Vehicle:
    """Mobile vehicle with position tracking."""

    def __init__(self, vehicle_id: str, xs: list, ys: list, speeds: list,
                 headings: list, timestamps: list):
        self.vehicle_id = vehicle_id
        self.xs = xs
        self.ys = ys
        self.speeds = speeds
        self.headings = headings
        self.timestamps = timestamps

    def get_position_at_time(self, sim_time_s: float) -> Tuple[float, float]:
        """Interpolate position at time."""
        time_idx = min(int(sim_time_s), len(self.xs) - 1)
        return (self.xs[time_idx], self.ys[time_idx])

    def get_speed_at_time(self, sim_time_s: float) -> float:
        """Get speed at time."""
        time_idx = min(int(sim_time_s), len(self.speeds) - 1)
        return self.speeds[time_idx]

    def get_heading_at_time(self, sim_time_s: float) -> float:
        """Get heading at time."""
        time_idx = min(int(sim_time_s), len(self.headings) - 1)
        return self.headings[time_idx]

    def is_active(self, sim_time_s: float) -> bool:
        """Check if vehicle is still in simulation."""
        return sim_time_s < len(self.timestamps)


class SimulationEnvironment:
    """Main simulation orchestrator."""

    def __init__(self):
        self.fog_nodes = {
            name: FogNode(name, info["pos"], info["initial_load"])
            for name, info in FOG_NODES.items()
        }
        self.cloud = None
        self.vehicles = {}

    def add_vehicle(self, vehicle: Vehicle) -> None:
        """Add a vehicle to simulation."""
        self.vehicles[vehicle.vehicle_id] = vehicle

    def execute_task_on_fog(self, step_MI: int, data_in_KB: float, fog_node: str,
                           vehicle_id: str, sim_time_s: float) -> Tuple[float, float]:
        """
        Execute task on fog node.
        Returns (latency_ms, energy_j).
        """
        fog = self.fog_nodes[fog_node]
        fog_load = fog.get_load()
        latency = t_exec_fog(step_MI, fog_load=fog_load) + t_tx_fog(data_in_KB)
        energy = step_energy(step_MI, data_in_KB, fog_node)
        return latency, energy

    def execute_task_on_cloud(self, step_MI: int, data_in_KB: float,
                             vehicle_id: str, sim_time_s: float) -> Tuple[float, float]:
        """
        Execute task on cloud.
        Returns (latency_ms, energy_j).
        """
        latency = t_exec_cloud(step_MI) + t_tx_cloud(data_in_KB)
        energy = step_energy(step_MI, data_in_KB, "cloud")
        return latency, energy

    def get_fog_state(self) -> Dict:
        """Get current state of all fog nodes."""
        return {
            name: {
                "load": node.get_load(),
                "queue": node.get_queue_length(),
                "pos": node.pos,
            }
            for name, node in self.fog_nodes.items()
        }

    def compute_t_exit_to_fog(self, vehicle_id: str, fog_node_name: str,
                             sim_time_s: float, fog_radius: float = FOG_RADIUS) -> float:
        """Compute T_exit for vehicle to fog node."""
        vehicle = self.vehicles[vehicle_id]
        vehicle_x, vehicle_y = vehicle.get_position_at_time(sim_time_s)
        speed_ms = vehicle.get_speed_at_time(sim_time_s)
        heading_deg = vehicle.get_heading_at_time(sim_time_s)

        fog = self.fog_nodes[fog_node_name]
        fog_x, fog_y = fog.pos

        t_exit = compute_t_exit(vehicle_x, vehicle_y, speed_ms, heading_deg,
                               fog_x, fog_y, fog_radius)
        return t_exit if t_exit != float("inf") else 10.0  # cap at 10s

    def update_fog_loads(self, dt_s: float = 1.0) -> None:
        """Update all fog nodes."""
        for node in self.fog_nodes.values():
            node.update(dt_s)


class CloudSimulator:
    """Simplified cloud model for instantaneous execution."""

    def execute(self, step_MI: int, data_in_KB: float) -> Tuple[float, float]:
        """Execute on cloud - instantaneous."""
        latency = t_exec_cloud(step_MI) + t_tx_cloud(data_in_KB)
        energy = step_energy(step_MI, data_in_KB, "cloud")
        return latency, energy


class TaskExecutor:
    """Abstract base for system-specific task execution."""

    def __init__(self, env: SimulationEnvironment):
        self.env = env

    def select_destination(self, vehicle_id: str, step_id: int, sim_time_s: float) -> str:
        """Select fog node or cloud. Returns 'A', 'B', 'C', 'D', or 'cloud'."""
        raise NotImplementedError
