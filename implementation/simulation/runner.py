"""
Complete simulation runner aligned with current task and broker models.
"""

from typing import Dict, List, Callable, Optional

import numpy as np
import simpy

from config import (
    AGENT2_STATE_DIM,
    FOG_NODES,
    N_VEHICLES,
    RANDOM_SEED,
    SIM_DURATION_S,
    TASK_RATE_HZ,
    TOTAL_DEADLINE_MS,
    WARMUP_S,
)
from broker.tof_broker import TOFBroker
from datasets import NetworkBandwidthTrace, TrajectoryGenerator
from environment.city import CityGrid
from environment.cloud import CloudServer
from environment.fog_node import FogNode
from environment.task import DAGTask, DAGStep, generate_dag_task
from environment.vehicle import Vehicle


class SmartCitySimulation:
    """Smart-city offloading simulation with fog-cloud infrastructure and DQNs."""

    def __init__(
        self,
        agent1,
        agent2,
        n_vehicles: int = N_VEHICLES,
        duration_s: float = SIM_DURATION_S,
        metrics_callback: Optional[Callable] = None,
        update_callback: Optional[Callable] = None,
    ):
        np.random.seed(RANDOM_SEED)

        self.env = simpy.Environment()
        self.agent1 = agent1
        self.agent2 = agent2
        self.n_vehicles = n_vehicles
        self.duration = duration_s
        self.metrics_callback = metrics_callback
        self.update_callback = update_callback

        self.city_grid = CityGrid()
        self.broker = TOFBroker()

        self.fog_nodes: Dict[str, FogNode] = {
            fog_id: FogNode(
                node_id=fog_id,
                position=fog_data["pos"],
                mips=fog_data.get("mips", 2000),
                env=self.env,
            )
            for fog_id, fog_data in FOG_NODES.items()
        }
        self.cloud = CloudServer(env=self.env)

        self.vehicles: Dict[str, Vehicle] = {}
        self.traj_gen = TrajectoryGenerator(num_vehicles=n_vehicles, duration_s=duration_s)
        self.trajectories = self.traj_gen.generate_fleet()

        self.network_trace = NetworkBandwidthTrace("urban_4g")

        self.metrics_history: List[Dict] = []
        self.completed_tasks: List[Dict] = []
        self.active_tasks: Dict[str, Dict] = {}

    def create_vehicles(self):
        for i in range(self.n_vehicles):
            vehicle_id = f"V{i:03d}"
            traj_data = self.trajectories[i % len(self.trajectories)]

            vehicle = Vehicle(
                vehicle_id=vehicle_id,
                position=traj_data["positions"][0],
                speed_kmh=float(traj_data["speeds"][0]),
                heading_deg=0.0,
                waypoints=traj_data["positions"],
            )
            self.vehicles[vehicle_id] = vehicle
            self.env.process(self.vehicle_task_generator(vehicle_id, traj_data))

    def vehicle_task_generator(self, vehicle_id: str, trajectory_data: Dict):
        vehicle = self.vehicles[vehicle_id]
        task_counter = 0
        update_interval = 1.0 / TASK_RATE_HZ

        while self.env.now < self.duration:
            vehicle.follow_trajectory(
                trajectory_waypoints=trajectory_data["positions"],
                trajectory_speeds=np.array(trajectory_data["speeds"]),
                sim_time=self.env.now,
            )

            task_id = f"{vehicle_id}-T{task_counter:05d}"
            dag = generate_dag_task(
                task_id=task_id,
                vehicle_id=vehicle_id,
                sim_time=self.env.now,
                spatial_tag={
                    "position": vehicle.position,
                    "speed_kmh": vehicle.speed_kmh,
                    "heading_deg": vehicle.heading_deg,
                },
            )
            task_payload = self._dag_to_payload(dag)

            available_fogs = self.city_grid.get_fog_in_range(vehicle.position)
            if not available_fogs:
                available_fogs = list(FOG_NODES.keys())

            dominant_step = self._dominant_offload_step(dag)
            task_class = self.broker.classify(dominant_step)

            if task_class == "boulder":
                destination = "cloud"
            else:
                state = self._build_state_vector(vehicle, available_fogs, task_payload)
                action = self.agent1.select_action(state)
                if action < len(available_fogs):
                    destination = available_fogs[action]
                elif action < len(FOG_NODES):
                    destination = ["A", "B", "C", "D"][action]
                else:
                    destination = "cloud"

            self.env.process(self.route_and_process_task(task_payload, destination))

            task_counter += 1
            yield self.env.timeout(update_interval)

    def route_and_process_task(self, task: Dict, destination: str):
        routing_action = self.agent2.select_action(self._build_sdn_state())
        if routing_action == 3:
            self.agent2.preinstall_vip_lane(f"{task['vehicle_id']}-{destination}", self.env.now)

        try:
            if destination == "cloud":
                self.cloud.enqueue_task(task)
                self.cloud.add_processing_process(task)
            else:
                fog_node = self.fog_nodes[destination]
                fog_node.enqueue_task(task, "ntb")
                fog_node.add_processing_process(task, "ntb")

            self.active_tasks[task["task_id"]] = {
                "destination": destination,
                "start_time": self.env.now,
                "vehicle_id": task["vehicle_id"],
            }
            self.register_task_callbacks(task)

        except Exception as e:
            print(f"Error routing task {task['task_id']}: {e}")

    def register_task_callbacks(self, task: Dict):
        def on_completion(done_task, _dest, _when):
            self.completed_tasks.append(done_task)
            self.active_tasks.pop(done_task["task_id"], None)

        def on_failure(failed_task, _dest, _when, _error):
            failed_task["failed"] = True
            self.active_tasks.pop(failed_task["task_id"], None)

        task["on_completion"] = on_completion
        task["on_failure"] = on_failure

    def _dominant_offload_step(self, dag: DAGTask) -> DAGStep:
        steps = [s for s in dag.steps.values() if s.assigned_to != "device"]
        return max(steps, key=lambda s: s.MI)

    def _dag_to_payload(self, dag: DAGTask) -> Dict:
        step_payload = {
            sid: {"MI": step.MI, "in_KB": step.in_KB, "out_KB": step.out_KB}
            for sid, step in dag.steps.items()
            if step.assigned_to != "device"
        }
        total_mi = sum(step["MI"] for step in step_payload.values())
        return {
            "task_id": dag.task_id,
            "created_at": dag.created_at,
            "vehicle_id": dag.vehicle_id,
            "vehicle_position": dag.spatial_tag.get("position", (0.0, 0.0)),
            "vehicle_speed": dag.spatial_tag.get("speed_kmh", 0.0),
            "input_size_kb": 200,
            "output_size_kb": 50,
            "deadline_ms": TOTAL_DEADLINE_MS,
            "steps": step_payload,
            "total_mi": total_mi,
            "priority": 0.5,
        }

    def _build_state_vector(self, vehicle: Vehicle, available_fogs: List[str], task: Dict) -> np.ndarray:
        fog_loads = []
        for fog_id in ["A", "B", "C", "D"]:
            if fog_id in available_fogs:
                fog_loads.append(self.fog_nodes[fog_id].get_load())
            else:
                fog_loads.append(1.0)

        bandwidth_ratio = float(np.mean(self.network_trace.bandwidth_mbps) / 100.0)

        state = np.array(
            [
                fog_loads[0],
                fog_loads[1],
                fog_loads[2],
                fog_loads[3],
                min(task.get("total_mi", 100.0) / 8000.0, 1.5),
                min(bandwidth_ratio, 1.0),
                min(vehicle.speed_kmh / 120.0, 1.0),
                1.0,
                max(0.0, min((TOTAL_DEADLINE_MS - task.get("deadline_ms", TOTAL_DEADLINE_MS)) / TOTAL_DEADLINE_MS, 1.0)),
                self.cloud.get_load(),
                min(len(self.active_tasks) / 200.0, 1.0),
                task.get("priority", 0.5),
                min(len(available_fogs) / 4.0, 1.0),
            ],
            dtype=np.float32,
        )
        return state

    def _build_sdn_state(self) -> np.ndarray:
        fog_loads = [self.fog_nodes[fid].get_load() for fid in ["A", "B", "C", "D"]]
        queue_levels = [min(self.fog_nodes[fid].get_queue_length() / 50.0, 1.0) for fid in ["A", "B", "C", "D"]]
        pending_super = min(len(self.active_tasks) / 200.0, 1.0)
        predicted_traffic = float(np.clip(np.std(self.network_trace.bandwidth_mbps) / 50.0, 0.0, 1.0))
        active_per_zone = [float(np.clip(np.random.uniform(0.1, 1.0), 0.0, 1.0)) for _ in range(4)]
        cloud_q = min(self.cloud.get_queue_length() / 100.0, 1.0)

        state = np.array(
            fog_loads + queue_levels + [pending_super, predicted_traffic] + active_per_zone + [cloud_q],
            dtype=np.float32,
        )
        if state.shape[0] != AGENT2_STATE_DIM:
            raise ValueError(f"Agent2 state mismatch: got {state.shape[0]}, expected {AGENT2_STATE_DIM}")
        return state

    def collect_metrics(self):
        if self.env.now < WARMUP_S:
            return

        total_tasks = len(self.completed_tasks)
        if total_tasks > 0:
            avg_latency = float(np.mean([t.get("total_latency_ms", 200.0) for t in self.completed_tasks]))
            deadline_met_count = sum(1 for t in self.completed_tasks if t.get("deadline_met", False))
            deadline_success = (deadline_met_count / total_tasks) * 100.0
            avg_energy = float(np.mean([t.get("energy_j", 0.1) for t in self.completed_tasks]))
        else:
            avg_latency = 0.0
            deadline_success = 0.0
            avg_energy = 0.0

        metrics = {
            "timestamp": self.env.now,
            "total_tasks": total_tasks,
            "active_tasks": len(self.active_tasks),
            "latency_ms": avg_latency,
            "energy_j": avg_energy,
            "deadline_success_pct": deadline_success,
            "fog_loads": {fid: fog.get_load() for fid, fog in self.fog_nodes.items()},
            "cloud_load": self.cloud.get_load(),
            "cloud_queue": self.cloud.get_queue_length(),
        }

        self.metrics_history.append(metrics)
        if self.metrics_callback:
            self.metrics_callback(metrics)
        return metrics

    def metrics_collector(self):
        while self.env.now < self.duration:
            self.collect_metrics()
            yield self.env.timeout(5.0)

    def realtime_updates(self):
        while self.env.now < self.duration:
            update_data = {
                "timestamp": self.env.now,
                "vehicles": [
                    {
                        "vehicle_id": vid,
                        "x": vehicle.position[0],
                        "y": vehicle.position[1],
                        "speed_kmh": vehicle.speed_kmh,
                    }
                    for vid, vehicle in self.vehicles.items()
                ],
                "fog_status": {fid: fog.get_status() for fid, fog in self.fog_nodes.items()},
                "cloud_status": self.cloud.get_status(),
                "completed_tasks": len(self.completed_tasks),
            }
            if self.update_callback:
                self.update_callback(update_data)
            yield self.env.timeout(1.0)

    def generate_results(self) -> Dict:
        total_completed = len(self.completed_tasks)
        if total_completed == 0:
            return {"error": "No tasks completed"}

        latencies = [t.get("total_latency_ms", 200.0) for t in self.completed_tasks]
        energies = [t.get("energy_j", 0.1) for t in self.completed_tasks]
        deadlines_met = sum(1 for t in self.completed_tasks if t.get("deadline_met", False))

        return {
            "total_tasks_completed": total_completed,
            "avg_latency_ms": float(np.mean(latencies)),
            "min_latency_ms": float(np.min(latencies)),
            "max_latency_ms": float(np.max(latencies)),
            "std_latency_ms": float(np.std(latencies)),
            "deadline_success_rate": (deadlines_met / total_completed) * 100.0,
            "avg_energy_j": float(np.mean(energies)),
            "total_energy_j": float(np.sum(energies)),
            "metrics_history": self.metrics_history,
        }

    def run(self) -> Dict:
        print("Initializing simulation...")
        self.create_vehicles()

        self.env.process(self.metrics_collector())
        if self.update_callback:
            self.env.process(self.realtime_updates())

        print(f"Running simulation for {self.duration}s...")
        self.env.run(until=self.duration)

        print("Simulation complete. Generating results...")
        return self.generate_results()


def run_simulation(
    agent1,
    agent2,
    sim_duration: float = SIM_DURATION_S,
    n_vehicles: int = N_VEHICLES,
    metrics_callback: Optional[Callable] = None,
    update_callback: Optional[Callable] = None,
) -> Dict:
    """Execute complete simulation and return aggregate results."""
    sim = SmartCitySimulation(
        agent1=agent1,
        agent2=agent2,
        n_vehicles=n_vehicles,
        duration_s=sim_duration,
        metrics_callback=metrics_callback,
        update_callback=update_callback,
    )
    return sim.run()
