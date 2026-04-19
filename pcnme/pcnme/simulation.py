"""
PCNME Simulation Engine
Core simulation loop and environment management.
"""

import numpy as np
from collections import deque
from .constants import (
    DAG, FOG_NODES, EC_THRESHOLD, Q_MAX, FOG_MIPS,
    FOG_RADIUS, WARMUP_S
)
from .formulas import (
    classify_step, compute_ec, step_latency, step_energy,
    compute_t_exit, select_handoff_mode
)


class FogNode:
    """Simulates a fog computing node."""

    def __init__(self, node_id: str, initial_load: float = 0.0):
        self.node_id = node_id
        self.cpu_load = initial_load
        self.task_queue = deque()
        self.current_task = None
        self.task_completion_time = 0.0

    def queue_task(self, task_id: str, exec_time_ms: float, arrival_time_s: float):
        """Queue a task at this fog node."""
        self.task_queue.append({
            'task_id': task_id,
            'exec_time_ms': exec_time_ms,
            'arrival_time_s': arrival_time_s,
        })

    def update(self, sim_time_s: float):
        """Update fog node state (process one task if possible)."""
        if self.current_task is None and self.task_queue:
            self.current_task = self.task_queue.popleft()
            self.task_completion_time = (sim_time_s +
                                         self.current_task['exec_time_ms'] / 1000.0)

        if self.current_task and sim_time_s >= self.task_completion_time:
            self.current_task = None

        # Update load
        if self.task_queue or self.current_task:
            self.cpu_load += 0.01  # Simple approximation
            self.cpu_load = min(0.99, self.cpu_load)
        else:
            self.cpu_load -= 0.01
            self.cpu_load = max(0.0, self.cpu_load)

    def get_queue_length(self):
        """Get current queue length."""
        return len(self.task_queue) + (1 if self.current_task else 0)


class Vehicle:
    """Simulates a vehicle with mobility and task execution."""

    def __init__(self, vehicle_id: str, trace: dict):
        self.vehicle_id = vehicle_id
        self.trace = trace  # {xs, ys, speeds, headings, timestamps}
        self.current_step = 0
        self.max_steps = len(trace['xs'])

    def get_position_at_time(self, sim_time_s: float):
        """Get vehicle position (x, y, speed, heading) at simulation time."""
        # Find closest trace point
        idx = max(0, min(int(sim_time_s), self.max_steps - 1))
        return {
            'x': self.trace['xs'][idx],
            'y': self.trace['ys'][idx],
            'speed_ms': self.trace['speeds'][idx],
            'heading_deg': self.trace['headings'][idx],
        }

    def is_active(self, sim_time_s: float):
        """Check if vehicle is still active in simulation."""
        return sim_time_s < self.trace['timestamps'][-1]


class SimulationEnvironment:
    """Main simulation environment orchestrating all entities."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.sim_time_s = 0.0
        self.dt = 1.0  # 1-second timestep

        # Initialize fog nodes
        self.fog_nodes = {}
        for node_id, node_info in FOG_NODES.items():
            self.fog_nodes[node_id] = FogNode(node_id, node_info['initial_load'])

        # Vehicles: set when simulation starts
        self.vehicles = {}

        # Statistics
        self.events_log = []
        self.task_records = []

    def initialize(self, vehicles: list):
        """Initialize vehicles for this simulation run."""
        self.vehicles = {}
        for vehicle_trace in vehicles:
            vehicle_id = vehicle_trace['vehicle_id']
            self.vehicles[vehicle_id] = Vehicle(vehicle_id, vehicle_trace)

    def get_fog_state(self):
        """Get current fog network state."""
        return {
            'loads': {nid: node.cpu_load for nid, node in self.fog_nodes.items()},
            'queues': {nid: node.get_queue_length()
                      for nid, node in self.fog_nodes.items()},
            'positions': {nid: FOG_NODES[nid]['pos'] for nid in self.fog_nodes},
        }

    def get_vehicle_state(self, vehicle_id: str):
        """Get current vehicle state."""
        if vehicle_id not in self.vehicles:
            return None

        vehicle = self.vehicles[vehicle_id]
        pos = vehicle.get_position_at_time(self.sim_time_s)

        return {
            'vehicle_id': vehicle_id,
            'position': (pos['x'], pos['y']),
            'speed_ms': pos['speed_ms'],
            'heading_deg': pos['heading_deg'],
            'is_active': vehicle.is_active(self.sim_time_s),
        }

    def compute_t_exit_to_fog(self, vehicle_id: str, fog_node_id: str):
        """Compute T_exit from vehicle to fog node."""
        if vehicle_id not in self.vehicles:
            return float('inf')

        vehicle = self.vehicles[vehicle_id]
        pos = vehicle.get_position_at_time(self.sim_time_s)
        fog_pos = FOG_NODES[fog_node_id]['pos']

        return compute_t_exit(
            vehicle_x=pos['x'],
            vehicle_y=pos['y'],
            speed_ms=pos['speed_ms'],
            heading_deg=pos['heading_deg'],
            fog_x=fog_pos[0],
            fog_y=fog_pos[1],
            fog_radius=FOG_RADIUS,
        )

    def is_vehicle_in_fog_range(self, vehicle_id: str, fog_node_id: str):
        """Check if vehicle is within fog coverage range."""
        if vehicle_id not in self.vehicles:
            return False

        vehicle = self.vehicles[vehicle_id]
        pos = vehicle.get_position_at_time(self.sim_time_s)
        fog_pos = FOG_NODES[fog_node_id]['pos']

        dist = np.sqrt((pos['x'] - fog_pos[0])**2 +
                       (pos['y'] - fog_pos[1])**2)

        return dist <= FOG_RADIUS

    def execute_task(self, task_id: str, step_id: int, destination: str,
                     vehicle_id: str):
        """
        Execute a single DAG step at specified destination.

        Args:
            task_id: unique task identifier
            step_id: DAG step index (1-5)
            destination: 'cloud' or fog node ID ('A', 'B', 'C', 'D')
            vehicle_id: associated vehicle

        Returns:
            dict with execution results (latency, energy, success)
        """
        if step_id not in DAG:
            raise ValueError(f"Invalid step ID: {step_id}")

        step_info = DAG[step_id]
        step_MI = step_info['MI']
        data_KB = step_info['in_KB']

        # Get current fog state
        fog_state = self.get_fog_state()

        # Compute latency
        if destination == 'cloud':
            latency_ms = step_latency(
                step_MI, data_KB, 'cloud', fog_load=None
            )
        else:
            fog_load = fog_state['loads'][destination]
            latency_ms = step_latency(
                step_MI, data_KB, destination, fog_load=fog_load
            )

        # Compute energy
        energy_j = step_energy(step_MI, data_KB, destination)

        # Check deadline
        deadline_ms = step_info.get('deadline_ms', 200.0)
        deadline_met = latency_ms <= deadline_ms

        return {
            'task_id': task_id,
            'step_id': step_id,
            'destination': destination,
            'vehicle_id': vehicle_id,
            'latency_ms': latency_ms,
            'energy_j': energy_j,
            'deadline_ms': deadline_ms,
            'deadline_met': deadline_met,
            'executed_at_s': self.sim_time_s,
        }

    def step(self):
        """Execute one simulation timestep."""
        # Update fog nodes
        for node in self.fog_nodes.values():
            node.update(self.sim_time_s)

        self.sim_time_s += self.dt

    def get_timestamp_in_warmup(self):
        """Check if current time is in warmup period."""
        return self.sim_time_s < WARMUP_S


class TaskExecutor:
    """Executes tasks according to system policy."""

    def __init__(self, env: SimulationEnvironment, system_name: str):
        self.env = env
        self.system_name = system_name

    def select_destination(self, step_id: int, vehicle_id: str,
                          fog_state: dict, agent=None) -> str:
        """
        Select execution destination (cloud or fog node).
        Override in system-specific implementations.

        Args:
            step_id: DAG step
            vehicle_id: vehicle ID
            fog_state: current fog network state
            agent: optional DQN agent for learning-based decisions

        Returns:
            destination: 'cloud' or fog node ID
        """
        raise NotImplementedError


class CloudSimulator:
    """Simplified cloud simulator (instantaneous model)."""

    def __init__(self):
        self.pending_tasks = {}

    def submit_task(self, task_id: str, step_id: int, vehicle_id: str):
        """Submit task to cloud."""
        self.pending_tasks[task_id] = {
            'step_id': step_id,
            'vehicle_id': vehicle_id,
            'submission_time_s': 0.0,  # set by caller
        }

    def complete_task(self, task_id: str):
        """Mark task as completed."""
        if task_id in self.pending_tasks:
            del self.pending_tasks[task_id]
