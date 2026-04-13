"""
UNIFIED SMART CITY TASK OFFLOADING SYSTEM
Application entrypoint for real-time simulation + dashboard.

Run: python app.py [system_type]
"""

import sys
import threading
import time
import json
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from collections import deque
from typing import Dict, List

import numpy as np
from flask_cors import CORS

from config import *
from agents.agent1 import Agent1
from agents.agent2 import Agent2
from broker.tof_broker import TOFBroker
from broker.tof_roles import TofLiteVehicleBroker, TofFogBroker
from datasets import NetworkBandwidthTrace
from environment.task import generate_dag_task
from mobility.handoff import TrajectoryPredictor, HTBBuffer
from sdn.controller import SDNController, FlowRule
from framework.contracts import (
    VehicleTaskSubmitted,
    FogDecisionMade,
    HandoffTriggered,
    CloudForwarded,
    TaskCompleted,
    make_envelope,
)
from framework.messaging import AtLeastOnceBus, StoreForwardBuffer, CircuitBreaker
from framework.policy import PolicyManagementService, PolicySyncClient
from framework.security import IdentityRegistry, DeviceIdentity
from app_runtime.api_routes import register_runtime_routes
from visualization.websocket_server import WebSocketServer, SystemMetrics
from visualization.api_server import (
    app as api_app,
    add_metrics,
    add_runtime_log,
    add_task_event,
    update_simulation_time,
    set_runtime_callbacks,
)
from results.logging_utils import setup_application_logger, write_json_event
from results.baseline_results import get_baseline_tracker


class UnifiedSmartCityApp:
    """Unified backend app with proactive offloading + live map streaming."""

    def __init__(self, system_type: str = "proposed"):
        self.system_type = system_type

        # Core intelligence
        self.agent1 = Agent1()
        self.agent2 = Agent2()
        self.broker = TOFBroker()
        self.vehicle_broker = TofLiteVehicleBroker(threshold=EC_THRESHOLD, fog_mips=FOG_MIPS)
        self.fog_broker = TofFogBroker(threshold=EC_THRESHOLD, fog_mips=FOG_MIPS)
        self.predictor = TrajectoryPredictor()
        self.sdn = SDNController()
        self.htb = HTBBuffer()
        self.bandwidth_trace = NetworkBandwidthTrace(profile="urban_4g", horizon_s=SIM_DURATION_S, sample_hz=10)

        # Framework services (control + data plane reliability/security)
        self.event_bus = AtLeastOnceBus(max_messages=8000)
        self.vehicle_store_forward = StoreForwardBuffer(capacity=3000)
        self.fog_store_forward = StoreForwardBuffer(capacity=3000)
        self.sdn_circuit_breaker = CircuitBreaker(fail_threshold=8, recovery_after=20)

        self.policy_service = PolicyManagementService()
        self.vehicle_policy = PolicySyncClient()
        self.fog_policy = PolicySyncClient()
        bundle = self.policy_service.get_bundle().__dict__
        self.vehicle_policy.sync(bundle)
        self.fog_policy.sync(bundle)

        self.identity_registry = IdentityRegistry()
        self.identity_registry.register(DeviceIdentity(device_id="cloud-orchestrator", role="cloud", cert_fingerprint="dev-cloud"))
        for i in range(N_VEHICLES):
            self.identity_registry.register(DeviceIdentity(device_id=f"V{i:03d}", role="vehicle", cert_fingerprint=f"veh-{i:03d}"))
        for fog_id in ["A", "B", "C", "D"]:
            self.identity_registry.register(DeviceIdentity(device_id=f"fog-{fog_id}", role="fog", cert_fingerprint=f"fog-{fog_id}"))

        # Runtime infra
        self.ws_server: WebSocketServer = None
        self.flask_app = api_app
        self.simulation_thread = None
        self.api_thread = None
        CORS(self.flask_app)

        self.logger = setup_application_logger("smart_city", "results/logs")
        self.json_event_log_path = "results/logs/events.jsonl"
        self.runtime_events = deque(maxlen=500)

        self.baseline_tracker = get_baseline_tracker()
        
        # Start tracking for this system type
        self.baseline_tracker.start_run(self.system_type)

        # Training state
        self.training_batch_count = 0
        self.retraining_in_progress = False
        self.bc_bootstrap_status = {
            "started": False,
            "completed": False,
            "agent1Pairs": 0,
            "agent2Pairs": 0,
            "lastError": None,
        }

        # Simulation state
        self.sim_time = 0
        self.running = False
        self.total_tasks = 0
        self.deadline_met_tasks = 0
        self.total_latency_ms = 0.0
        self.total_energy_j = 0.0
        self.relay_device_to_fog_total_ms = 0.0
        self.relay_fog_to_cloud_total_ms = 0.0
        self.relay_count = 0
        self.task_migrations = 0
        self.handoff_count = 0
        self.tasks_per_second = max(1, int(N_VEHICLES * 0.8))

        # Execution policy: tiny stays local, pebbles go fog (optionally batched), boulders go cloud
        self.device_mips = 1200.0
        self.local_step_mi_threshold = 80
        self.super_task_min_pebbles = 2

        # Agent analytics for UI observability
        self.agent_history = deque(maxlen=300)
        # Will be populated with real data from tracker
        self.nsga_summary = {}
        self.agent_stats = {
            "agent1": {
                "rewardSum": 0.0,
                "rewardCount": 0,
                "positiveRewards": 0,
                "penalties": 0,
                "updates": 0,
                "epsilon": float(self.agent1.epsilon),
                "decisions": {"local": 0, "fog": 0, "cloud": 0, "superTasks": 0},
            },
            "agent2": {
                "rewardSum": 0.0,
                "rewardCount": 0,
                "positiveRewards": 0,
                "penalties": 0,
                "updates": 0,
                "epsilon": float(self.agent2.epsilon),
            },
        }

        self.logic_snapshot = {
            "simulationTime": 0,
            "running": False,
            "systemType": self.system_type,
            "vehiclesTotal": N_VEHICLES,
            "tasksTotal": 0,
            "deadlineMet": 0,
            "deadlineRate": 0.0,
            "avgLatencyMs": 0.0,
            "avgEnergyJ": 0.0,
            "localExec": 0,
            "fogExec": 0,
            "cloudExec": 0,
            "superTasks": 0,
            "offloadsActive": 0,
            "handoffs": 0,
            "taskMigrations": 0,
            "sdnReactive": 0,
            "sdnPreinstallHits": 0,
            "sdnPacketDrops": 0,
            "relayDeviceToFogMs": 0.0,
            "relayFogToCloudMs": 0.0,
            "busPublished": 0,
            "busDedupDropped": 0,
            "vehicleBuffer": 0,
            "fogBuffer": 0,
        }
        self.task_events = deque(maxlen=400)

        # Live map state
        self.vehicle_states: List[Dict] = []
        self.trajectory_paths: Dict[str, List[Dict]] = {}
        self.handoff_events = []  # Recent handoff events for visualization
        self.map_state = {
            "city": "Istanbul",
            "bounds": {"xMin": 0, "xMax": 1000, "yMin": 0, "yMax": 1000},
            "fogNodes": [],
            "cloud": {"x": 500, "y": 500, "name": "Cloud"},
            "vehicles": [],
            "connections": [],  # All active connections (device->fog, fog->fog, fog->cloud)
            "offloads": [],  # Task offload visualization (subset of connections)
            "handoffs": [],  # Handoff transitions
            "trajectories": [],  # Vehicle trajectory predictions
            "simulationTime": 0,
        }

        self._setup_api_routes()
        self._initialize_live_map()
        self._log_event("info", "bandwidth_trace_initialized", source=self.bandwidth_trace.source)

        set_runtime_callbacks(
            start_callback=self._api_start_simulation,
            stop_callback=self._api_stop_simulation,
            reset_callback=self._api_reset_simulation,
            logic_callback=self._api_logic_snapshot,
            tasks_callback=self._api_recent_tasks,
            logs_callback=self._api_recent_logs,
        )

        print("\n" + "=" * 80)
        print(" SMART CITY VEHICULAR TASK OFFLOADING SYSTEM - UNIFIED ENTRY POINT")
        print("=" * 80)
        self._log_event("info", "app_initialized", system_type=self.system_type)

    def _log_event(self, level: str, event: str, **data):
        payload = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "simulationTime": float(self.sim_time),
            **data,
        }
        self.runtime_events.append(payload)
        add_runtime_log(payload)
        write_json_event(self.json_event_log_path, payload)
        message = json.dumps(payload, ensure_ascii=True)
        if level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)
        else:
            self.logger.info(message)

    def _publish_contract_event(self, topic: str, event_type: str, event_id: str, payload_obj):
        if hasattr(payload_obj, "__dict__"):
            payload = dict(payload_obj.__dict__)
        else:
            payload = dict(payload_obj)
        envelope = make_envelope(
            event_type=event_type,
            event_id=event_id,
            timestamp=datetime.now().isoformat(),
            payload=payload,
        ).to_dict()
        accepted = self.event_bus.publish(topic=topic, message_id=event_id, payload=envelope)
        if accepted:
            self._log_event("info", "contract_event_published", topic=topic, eventType=event_type, eventId=event_id)
        return accepted

    def _api_start_simulation(self, system_type: str):
        if system_type in ["baseline1", "baseline2", "baseline3", "proposed"]:
            self.system_type = system_type
            self.logic_snapshot["systemType"] = system_type

        if self.running:
            return {"running": True, "started": False}

        if self.sim_time >= SIM_DURATION_S:
            self._api_reset_simulation()

        self.running = True
        self.logic_snapshot["running"] = True
        self.simulation_thread = threading.Thread(target=self._run_simulation_worker, daemon=True)
        self.simulation_thread.start()
        self._log_event("info", "simulation_started", system_type=self.system_type)
        return {"running": True, "started": True}

    def _api_stop_simulation(self):
        self.running = False
        self.logic_snapshot["running"] = False
        # Finalize baseline results on manual stop
        if self.sim_time > 0:
            self.baseline_tracker.finalize_run(self.sim_time)
        self._log_event("warning", "simulation_stopped")
        return {"running": False, "stopped": True}

    def _api_reset_simulation(self):
        self.running = False
        self.sim_time = 0
        self.total_tasks = 0
        self.deadline_met_tasks = 0
        self.total_latency_ms = 0.0
        self.total_energy_j = 0.0
        self.relay_device_to_fog_total_ms = 0.0
        self.relay_fog_to_cloud_total_ms = 0.0
        self.relay_count = 0
        self.task_migrations = 0
        self.handoff_count = 0
        self.task_events.clear()
        self.logic_snapshot.update({
            "simulationTime": 0,
            "running": False,
            "tasksTotal": 0,
            "deadlineMet": 0,
            "deadlineRate": 0.0,
            "avgLatencyMs": 0.0,
            "avgEnergyJ": 0.0,
            "localExec": 0,
            "fogExec": 0,
            "cloudExec": 0,
            "superTasks": 0,
            "offloadsActive": 0,
            "handoffs": 0,
            "taskMigrations": 0,
            "sdnReactive": 0,
            "sdnPreinstallHits": 0,
            "sdnPacketDrops": 0,
            "relayDeviceToFogMs": 0.0,
            "relayFogToCloudMs": 0.0,
            "busPublished": 0,
            "busDedupDropped": 0,
            "vehicleBuffer": 0,
            "fogBuffer": 0,
        })
        self._log_event("info", "simulation_reset")
        return {"running": False, "reset": True}

    def _api_logic_snapshot(self):
        return {
            "logic": self.logic_snapshot,
            "agent": self._build_agent_snapshot(),
            "bootstrap": self.bc_bootstrap_status,
        }

    def _api_recent_tasks(self):
        return list(self.task_events)

    def _api_recent_logs(self):
        return list(self.runtime_events)

    def _setup_api_routes(self):
        """Add runtime API routes."""
        register_runtime_routes(self)

    def _generate_fog_state(self) -> Dict:
        fog_state = {}
        for fog_id in ["A", "B", "C", "D"]:
            fog_state[fog_id] = float(np.clip(FOG_NODES[fog_id].get("load", 0.3) + np.random.uniform(-0.1, 0.1), 0.05, 0.95))
            fog_state[f"queue_{fog_id}"] = int(np.random.randint(0, 50))
            fog_state[f"active_{fog_id}"] = float(np.random.uniform(0.1, 1.0))
        fog_state["bandwidth_util"] = float(np.random.uniform(0.2, 0.9))
        fog_state["vehicle_speed"] = float(np.random.uniform(20, 100))
        fog_state["T_exit"] = float(np.random.uniform(1.0, 10.0))
        fog_state["deadline_remaining"] = float(np.random.uniform(30, TOTAL_DEADLINE_MS))
        fog_state["cloud_load"] = float(np.random.uniform(0.1, 0.9))
        fog_state["cloud_queue"] = int(np.random.randint(0, 100))
        fog_state["pending_super"] = float(np.random.uniform(0.0, 1.0))
        return fog_state

    def _bootstrap_behavioral_cloning(self):
        """Run TOF + MMDE-NSGA-II offline bootstrap and pretrain both agents."""
        if self.bc_bootstrap_status["started"]:
            return
        self.bc_bootstrap_status["started"] = True

        if not ENABLE_BOOTSTRAP_PRETRAIN:
            self.bc_bootstrap_status["completed"] = False
            self.bc_bootstrap_status["lastError"] = "disabled_by_config"
            self._log_event("warning", "bc_bootstrap_disabled")
            return

        try:
            from optimizer.nsga2_mmde import run_nsga2_mmde

            agent1_pairs_count = 0
            agent2_pairs_count = 0
            started_at = time.time()

            for i in range(int(max(1, BOOTSTRAP_TASKS))):
                if (time.time() - started_at) > float(BOOTSTRAP_MAX_SECONDS):
                    self._log_event(
                        "warning",
                        "bc_bootstrap_time_budget_reached",
                        elapsed_s=round(time.time() - started_at, 3),
                    )
                    break

                task = generate_dag_task(
                    task_id=f"BOOT-T{i:03d}",
                    vehicle_id=f"BOOT-V{i % max(1, N_VEHICLES):03d}",
                    sim_time=float(i),
                    spatial_tag={"position": (500, 500), "speed_kmh": 50.0, "heading_deg": 0.0},
                )

                split = self.broker.process_dag(task)
                pebble_steps = split.get("pebbles", [])
                if not pebble_steps:
                    continue

                fog_states = self._generate_fog_state()
                pareto_result = run_nsga2_mmde(
                    pebble_steps,
                    fog_states,
                    pop_size=int(max(4, BOOTSTRAP_NSGA_POP_SIZE)),
                    n_gens=int(max(2, BOOTSTRAP_NSGA_GENS)),
                )
                agent1_pairs_count += self.agent1.pretrain_from_tof_mmde_nsga2(
                    pebble_steps=pebble_steps,
                    fog_states=fog_states,
                    pareto_result=pareto_result,
                    epochs=1,
                )
                agent2_pairs_count += self.agent2.pretrain_from_tof_mmde_nsga2(
                    fog_states=fog_states,
                    pareto_result=pareto_result,
                    epochs=1,
                )

            self.bc_bootstrap_status["agent1Pairs"] = agent1_pairs_count
            self.bc_bootstrap_status["agent2Pairs"] = agent2_pairs_count
            self.bc_bootstrap_status["completed"] = (agent1_pairs_count > 0 and agent2_pairs_count > 0)
            self.bc_bootstrap_status["lastError"] = None
            print(f"[BC] Bootstrap complete | agent1_pairs={agent1_pairs_count} agent2_pairs={agent2_pairs_count}")
            self._log_event("info", "bc_bootstrap_complete", agent1_pairs=agent1_pairs_count, agent2_pairs=agent2_pairs_count)
        except KeyboardInterrupt:
            # Do not crash app startup if user interrupts optimization.
            self.bc_bootstrap_status["completed"] = False
            self.bc_bootstrap_status["lastError"] = "interrupted"
            self._log_event("warning", "bc_bootstrap_interrupted")
        except Exception as e:
            self.bc_bootstrap_status["completed"] = False
            self.bc_bootstrap_status["lastError"] = str(e)
            print(f"[BC] Bootstrap skipped/failed: {e}")
            self._log_event("error", "bc_bootstrap_failed", error=str(e))

    def _record_agent_reward(self, agent_key: str, reward: float):
        stats = self.agent_stats[agent_key]
        stats["rewardSum"] += float(reward)
        stats["rewardCount"] += 1
        if reward >= 0:
            stats["positiveRewards"] += 1
        else:
            stats["penalties"] += 1

    def _record_agent_update(self, agent_key: str):
        self.agent_stats[agent_key]["updates"] += 1

    def _build_agent_snapshot(self) -> Dict:
        a1 = self.agent_stats["agent1"]
        a2 = self.agent_stats["agent2"]
        return {
            "timestamp": datetime.now().isoformat(),
            "simulationTime": float(self.sim_time),
            "agent1": {
                **a1,
                "avgReward": (a1["rewardSum"] / a1["rewardCount"]) if a1["rewardCount"] else 0.0,
                "rewardRate": (a1["positiveRewards"] / a1["rewardCount"]) if a1["rewardCount"] else 0.0,
                "epsilon": float(self.agent1.epsilon),
            },
            "agent2": {
                **a2,
                "avgReward": (a2["rewardSum"] / a2["rewardCount"]) if a2["rewardCount"] else 0.0,
                "rewardRate": (a2["positiveRewards"] / a2["rewardCount"]) if a2["rewardCount"] else 0.0,
                "epsilon": float(self.agent2.epsilon),
            },
        }

    def _initialize_live_map(self):
        """Initialize fog placement and vehicle trajectories."""
        fog_nodes = []
        coverage_zones = []
        for fog_id, fog_data in FOG_NODES.items():
            x, y = fog_data["pos"]
            fog_nodes.append(
                {
                    "id": fog_id,
                    "name": fog_data.get("name", f"Fog-{fog_id}"),
                    "x": float(x),
                    "y": float(y),
                    "coverage": float(FOG_COVERAGE_RADIUS),
                    "load": float(fog_data.get("load", 0.3)),
                }
            )
            # Add coverage zone for visualization
            coverage_zones.append({
                "fogId": fog_id,
                "center": {"x": float(x), "y": float(y)},
                "radius": float(FOG_COVERAGE_RADIUS),
                "name": fog_data.get("name", f"Fog-{fog_id}"),
            })

        self.map_state["fogNodes"] = fog_nodes
        self.map_state["coverageZones"] = coverage_zones

        # Prefer recorded trajectories so mobility and handoff behavior are realistic and reproducible.
        self.trajectory_paths = self._load_trajectory_paths(max_vehicles=N_VEHICLES)

        self.vehicle_states = []
        trajectory_ids = sorted(self.trajectory_paths.keys())
        for i in range(N_VEHICLES):
            source_id = trajectory_ids[i] if i < len(trajectory_ids) else None
            path = self.trajectory_paths.get(source_id, []) if source_id else []

            if path:
                p0 = path[0]
                x = float(p0["x"])
                y = float(p0["y"])
                heading = float(p0["heading_deg"])
                speed = float(p0["speed_kmh"])
            else:
                x = float(np.random.uniform(50, 950))
                y = float(np.random.uniform(50, 950))
                heading = float(np.random.uniform(0, 360))
                speed = float(np.random.uniform(30, 100))

            speed_ms = speed * (1000.0 / 3600.0)
            vx = speed_ms * np.cos(np.radians(heading))
            vy = speed_ms * np.sin(np.radians(heading))
            self.vehicle_states.append(
                {
                    "id": f"V{i:03d}",
                    "sourceTrajectoryId": source_id,
                    "traj": path,
                    "traj_idx": 0,
                    "x": x,
                    "y": y,
                    "heading": heading,
                    "speed_kmh": speed,
                    "speed_ms": speed_ms,
                    "vx": float(vx),
                    "vy": float(vy),
                }
            )

    def _load_trajectory_paths(self, max_vehicles: int) -> Dict[str, List[Dict]]:
        """Load trajectory points from CARLA CSV (results/carla_trajectories.csv)."""
        csv_path = Path("results") / "carla_trajectories.csv"
        if not csv_path.exists():
            return {}

        grouped: Dict[str, List[Dict]] = defaultdict(list)
        try:
            with csv_path.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    vid = row.get("vehicle_id")
                    if not vid:
                        continue
                    grouped[vid].append(
                        {
                            "t": float(row.get("timestamp_s", 0.0)),
                            "x": float(row.get("position_x", 0.0)),
                            "y": float(row.get("position_y", 0.0)),
                            "speed_kmh": float(row.get("speed_kmh", 0.0)),
                            "heading_deg": float(row.get("heading_deg", 0.0)),
                        }
                    )
        except Exception as e:
            self._log_event("warning", "trajectory_csv_load_failed", error=str(e))
            return {}

        selected = sorted(grouped.keys())[:max_vehicles]
        out: Dict[str, List[Dict]] = {}
        for vid in selected:
            path = sorted(grouped[vid], key=lambda p: p["t"])
            for p in path:
                p["x"] = float(np.clip(p["x"], 0.0, 1000.0))
                p["y"] = float(np.clip(p["y"], 0.0, 1000.0))
                p["speed_kmh"] = float(np.clip(p["speed_kmh"], 0.0, 140.0))
                p["heading_deg"] = float(p["heading_deg"] % 360.0)
            out[vid] = path

        self._log_event("info", "trajectory_csv_loaded", trajectories=len(out))
        return out

    def _retrain_agents_online(self):
        """Simple online fine-tuning loop from rolling runtime signals."""
        try:
            print("[RETRAINING] Starting online learning")
            self._log_event("info", "retraining_started")
            # Synthetic reward replay from recent performance trend.
            for _ in range(200):
                s1 = np.random.random(AGENT1_STATE_DIM).astype(np.float32)
                a1 = np.random.randint(0, AGENT1_ACTION_DIM)
                r1 = float(np.random.uniform(-0.3, 0.8))
                ns1 = np.random.random(AGENT1_STATE_DIM).astype(np.float32)
                self.agent1.store(s1, a1, r1, ns1, False)
                self.agent1.update()

                s2 = np.random.random(AGENT2_STATE_DIM).astype(np.float32)
                a2 = np.random.randint(0, AGENT2_ACTION_DIM)
                r2 = float(np.random.uniform(-0.2, 0.6))
                ns2 = np.random.random(AGENT2_STATE_DIM).astype(np.float32)
                self.agent2.store(s2, a2, r2, ns2, False)
                self.agent2.update()

            self.training_batch_count += 1
            print("[RETRAINING] Completed")
            self._log_event("info", "retraining_completed", batch_count=self.training_batch_count)
        except Exception as e:
            print(f"[RETRAINING] Error: {e}")
            self._log_event("error", "retraining_failed", error=str(e))
        finally:
            self.retraining_in_progress = False

    def _initialize_websocket(self, host="127.0.0.1", port=8765):
        self.ws_server = WebSocketServer(host, port)
        print(f"[INIT] WebSocket: ws://{host}:{port}")

    def _vehicle_move(self, vehicle: Dict):
        traj = vehicle.get("traj") or []
        if traj:
            next_idx = (int(vehicle.get("traj_idx", 0)) + 1) % len(traj)
            p = traj[next_idx]
            vehicle["traj_idx"] = next_idx
            vehicle["x"] = float(p["x"])
            vehicle["y"] = float(p["y"])
            vehicle["heading"] = float(p["heading_deg"])
            vehicle["speed_kmh"] = float(p["speed_kmh"])
            vehicle["speed_ms"] = vehicle["speed_kmh"] * (1000.0 / 3600.0)
            heading_rad = np.radians(vehicle["heading"])
            vehicle["vx"] = float(vehicle["speed_ms"] * np.cos(heading_rad))
            vehicle["vy"] = float(vehicle["speed_ms"] * np.sin(heading_rad))
            return

        vehicle["x"] += vehicle["vx"]
        vehicle["y"] += vehicle["vy"]

        # reflect at boundaries
        if vehicle["x"] < 20 or vehicle["x"] > 980:
            vehicle["vx"] *= -1
            vehicle["x"] = float(np.clip(vehicle["x"], 20, 980))
            vehicle["heading"] = (180.0 - vehicle["heading"]) % 360
        if vehicle["y"] < 20 or vehicle["y"] > 980:
            vehicle["vy"] *= -1
            vehicle["y"] = float(np.clip(vehicle["y"], 20, 980))
            vehicle["heading"] = (-vehicle["heading"]) % 360

    def _bandwidth_at_simtime(self) -> float:
        trace = self.bandwidth_trace.bandwidth_mbps
        if trace is None or len(trace) == 0:
            return float(BANDWIDTH_MBPS)
        idx = int((self.sim_time * 10) % len(trace))
        return float(trace[idx])

    def _nearest_fog(self, x: float, y: float) -> str:
        best_id = "A"
        best_dist = 1e18
        for fog_id, fog in FOG_NODES.items():
            fx, fy = fog["pos"]
            d = (x - fx) ** 2 + (y - fy) ** 2
            if d < best_dist:
                best_dist = d
                best_id = fog_id
        return best_id

    def _build_agent1_state(self, vehicle: Dict, step_mi: int, deadline_remaining_ms: float) -> np.ndarray:
        loads = []
        for fog_id in ["A", "B", "C", "D"]:
            base = FOG_NODES[fog_id].get("load", 0.3)
            dyn = float(np.clip(base + np.random.uniform(-0.08, 0.08), 0.05, 0.95))
            loads.append(dyn)

        bw = self._bandwidth_at_simtime()
        bw_util = float(np.clip(1.0 - (bw / 120.0), 0.05, 1.0))
        t_exit = self.predictor.compute_t_exit(
            (vehicle["x"], vehicle["y"]), vehicle["speed_ms"], vehicle["heading"], self._nearest_fog(vehicle["x"], vehicle["y"])
        )
        if t_exit == float("inf"):
            t_exit = 10.0

        vec = np.array(
            [
                loads[0],
                loads[1],
                loads[2],
                loads[3],
                min(step_mi / 8000.0, 1.5),
                bw_util,
                min(vehicle["speed_kmh"] / 120.0, 1.0),
                min(t_exit / 10.0, 1.0),
                max(0.0, min(deadline_remaining_ms / 200.0, 1.0)),
                float(np.random.uniform(0.15, 0.65)),
                float(np.random.uniform(0.0, 1.0)),
                float(np.random.uniform(0.0, 1.0)),
                float(np.random.uniform(0.0, 1.0)),
            ],
            dtype=np.float32,
        )
        return vec

    def _build_agent2_state(self) -> np.ndarray:
        util = [float(np.random.uniform(0.2, 0.95)) for _ in range(4)]
        qdepth = [float(np.random.uniform(0.0, 1.0)) for _ in range(4)]
        pending_super = float(np.random.uniform(0.0, 1.0))
        pred_traffic = float(np.random.uniform(0.0, 1.0))
        active_per_zone = [float(np.random.uniform(0.1, 1.0)) for _ in range(4)]
        cloud_q = float(np.random.uniform(0.0, 1.0))
        return np.array(util + qdepth + [pending_super, pred_traffic] + active_per_zone + [cloud_q], dtype=np.float32)

    def _destination_from_action(self, action: int) -> str:
        if action == 0:
            return "A"
        if action == 1:
            return "B"
        if action == 2:
            return "C"
        if action == 3:
            return "D"
        return "CLOUD"

    def _network_delay_ms(self, action2: int, src: str, dst: str, flow_id: str, payload_kb: float = 50.0) -> Dict:
        # Agent 2 action map: 0 primary,1 alt1,2 alt2,3 reserve_vip,4 best_effort
        path_name = f"{src}-{dst}-a{action2}"
        if action2 == 3:
            rule = FlowRule(flow_id=path_name, priority=100, match_criteria={"src": src, "dst": dst}, actions=["forward"])
            self.sdn.install_rule("sw-core", rule, install_time=float(self.sim_time))
            self.agent2.preinstall_vip_lane(path_name, float(self.sim_time), duration=12.0)

        bw = self._bandwidth_at_simtime()
        queue_pressure = float(np.clip(1.0 - (bw / 100.0) + np.random.uniform(-0.08, 0.08), 0.0, 1.0))
        return self.sdn.route_by_policy(
            flow_id=flow_id,
            source=src,
            destination=dst,
            policy_action=int(action2),
            sim_time=float(self.sim_time),
            payload_kb=float(payload_kb),
            queue_pressure=queue_pressure,
        )

    def _execute_local_step(self, step) -> tuple:
        """Execute very small steps on the vehicle (IoT device)."""
        local_exec_s = step.MI / self.device_mips
        local_latency_ms = local_exec_s * 1000.0 + float(np.random.uniform(0.2, 1.2))
        local_energy_j = (step.in_KB / 1024.0) * 0.006 + (local_exec_s * 0.03)
        return local_latency_ms, local_energy_j

    def _execute_remote_unit(
        self,
        vehicle: Dict,
        destination: str,
        unit_mi: float,
        unit_in_kb: float,
        unit_id: str,
        unit_class: str,
        mode: str,
        offloads: List[Dict],
    ) -> tuple:
        """Execute one remote offloading unit (single step or super-task)."""
        src_zone = self._nearest_fog(vehicle["x"], vehicle["y"])
        s2 = self._build_agent2_state()
        a2 = self.agent2.select_action(s2)
        policy_features = self.fog_policy.current_bundle.get("rules", {}).get("features", {}) if self.fog_policy.current_bundle else {}
        enable_relay = bool(policy_features.get("enableFogCloudRelay", True))
        enable_store_forward = bool(policy_features.get("enableStoreForward", True))
        enable_circuit_breaker = bool(policy_features.get("enableCircuitBreaker", True))

        # Access leg from vehicle to ingress fog.
        access_tx_ms = (float(unit_in_kb) * 8.0) / (BANDWIDTH_MBPS * 1000.0) * 1000.0
        access_delay_ms = float(access_tx_ms + G5_LATENCY_MS + np.random.uniform(0.8, 2.8))

        relay_info = None
        network_info = None
        if destination == "CLOUD" and enable_relay:
            cb_open = self.sdn_circuit_breaker.is_open(int(self.sim_time)) if enable_circuit_breaker else False
            if cb_open and enable_store_forward:
                self.fog_store_forward.push(
                    {
                        "taskId": unit_id,
                        "vehicleId": vehicle["id"],
                        "fromFog": src_zone,
                        "to": "CLOUD",
                        "payloadKB": float(unit_in_kb),
                        "queuedAt": float(self.sim_time),
                    }
                )
                relay_info = {
                    "policy_name": "circuit_breaker_buffer",
                    "preinstalled": False,
                    "packet_drop": False,
                    "ctrl_overhead_ms": 0.0,
                    "total_delay_ms": 15.0,
                }
            else:
                relay_info = self._network_delay_ms(a2, src_zone, "CLOUD", f"{unit_id}:relay", payload_kb=unit_in_kb)
                if relay_info.get("packet_drop", False):
                    self.sdn_circuit_breaker.on_failure(int(self.sim_time))
                    if enable_store_forward:
                        self.fog_store_forward.push(
                            {
                                "taskId": unit_id,
                                "vehicleId": vehicle["id"],
                                "fromFog": src_zone,
                                "to": "CLOUD",
                                "payloadKB": float(unit_in_kb),
                                "queuedAt": float(self.sim_time),
                            }
                        )
                else:
                    self.sdn_circuit_breaker.on_success()

                self._publish_contract_event(
                    topic="cloud_forwarded",
                    event_type="cloud_forwarded",
                    event_id=f"cloud_forwarded:{unit_id}",
                    payload_obj=CloudForwarded(
                        task_id=unit_id,
                        ingress_fog=src_zone,
                        cloud_id="CLOUD",
                        payload_kb=float(unit_in_kb),
                    ),
                )
            network_info = relay_info
            net_delay_ms = float(access_delay_ms + relay_info.get("total_delay_ms", 0.0))
            self.relay_device_to_fog_total_ms += access_delay_ms
            self.relay_fog_to_cloud_total_ms += float(relay_info.get("total_delay_ms", 0.0))
            self.relay_count += 1
        else:
            network_info = self._network_delay_ms(a2, src_zone, destination, unit_id, payload_kb=unit_in_kb)
            net_delay_ms = float(network_info.get("total_delay_ms", 0.0))

        if destination == "CLOUD":
            t_exec = unit_mi / CLOUD_MIPS
            dst_x, dst_y = self.map_state["cloud"]["x"], self.map_state["cloud"]["y"]
            dst_type = "cloud"
            self.logic_snapshot["cloudExec"] += 1
        else:
            fog_load = float(np.clip(FOG_NODES[destination].get("load", 0.3) + np.random.uniform(-0.1, 0.1), 0.05, 0.95))
            t_exec = self.predictor.compute_t_exec(unit_mi, destination, fog_load)
            dst_x, dst_y = FOG_NODES[destination]["pos"]
            dst_type = "fog"
            self.logic_snapshot["fogExec"] += 1

        compute_ms = t_exec * 1000.0
        total_latency_ms = compute_ms + net_delay_ms
        energy_j = (unit_in_kb / 1024.0) * 0.01 + (compute_ms / 1000.0) * 0.02

        delivery_ratio = 1.0 if total_latency_ms < TOTAL_DEADLINE_MS else 0.0
        pre_hit = bool(network_info.get("preinstalled", False))
        packet_drop = bool(network_info.get("packet_drop", False))
        ctrl_overhead_ms = float(network_info.get("ctrl_overhead_ms", 0.0))
        reward2 = self.agent2.compute_reward(delivery_ratio, net_delay_ms, ctrl_overhead_ms, packet_drop, pre_hit)
        ns2 = self._build_agent2_state()
        self.agent2.store(s2, a2, reward2, ns2, False)
        self.agent2.update()
        self._record_agent_reward("agent2", reward2)
        self._record_agent_update("agent2")

        if destination == "CLOUD" and enable_relay:
            fog_x, fog_y = FOG_NODES[src_zone]["pos"]
            offloads.append(
                {
                    "taskId": f"{unit_id}:d2f",
                    "vehicleId": vehicle["id"],
                    "from": {"x": round(vehicle["x"], 2), "y": round(vehicle["y"], 2)},
                    "to": {"x": float(fog_x), "y": float(fog_y), "type": "fog", "id": src_zone},
                    "class": unit_class,
                    "mode": mode,
                    "leg": "device_to_fog",
                    "network": {
                        "policy": "access",
                        "preinstalled": False,
                        "packetDrop": False,
                        "delayMs": round(access_delay_ms, 3),
                    },
                }
            )
            offloads.append(
                {
                    "taskId": f"{unit_id}:f2c",
                    "vehicleId": vehicle["id"],
                    "from": {"x": float(fog_x), "y": float(fog_y)},
                    "to": {"x": float(dst_x), "y": float(dst_y), "type": "cloud", "id": destination},
                    "class": unit_class,
                    "mode": mode,
                    "leg": "fog_to_cloud",
                    "network": {
                        "policy": network_info.get("policy_name", "primary"),
                        "preinstalled": pre_hit,
                        "packetDrop": packet_drop,
                        "delayMs": round(float(network_info.get("total_delay_ms", 0.0)), 3),
                    },
                }
            )
        else:
            offloads.append(
                {
                    "taskId": unit_id,
                    "vehicleId": vehicle["id"],
                    "from": {"x": round(vehicle["x"], 2), "y": round(vehicle["y"], 2)},
                    "to": {"x": float(dst_x), "y": float(dst_y), "type": dst_type, "id": destination},
                    "class": unit_class,
                    "mode": mode,
                    "leg": "single_hop",
                    "network": {
                        "policy": network_info.get("policy_name", "primary"),
                        "preinstalled": pre_hit,
                        "packetDrop": packet_drop,
                        "delayMs": round(net_delay_ms, 3),
                    },
                }
            )

        task_event = {
            "taskId": unit_id,
            "vehicleId": vehicle["id"],
            "class": unit_class,
            "destination": destination,
            "latencyMs": round(total_latency_ms, 3),
            "energyJ": round(energy_j, 4),
            "mode": mode,
            "networkPolicy": network_info.get("policy_name", "primary"),
            "networkPreinstalled": pre_hit,
            "networkPacketDrop": packet_drop,
            "networkDelayMs": round(net_delay_ms, 3),
            "networkCtrlOverheadMs": round(ctrl_overhead_ms, 3),
            "relayDeviceToFogMs": round(access_delay_ms if destination == "CLOUD" and enable_relay else 0.0, 3),
            "relayFogToCloudMs": round(float(network_info.get("total_delay_ms", 0.0)) if destination == "CLOUD" and enable_relay else 0.0, 3),
        }
        self.task_events.append(task_event)
        add_task_event(task_event)

        return total_latency_ms, energy_j

    def _simulate_one_dag(self, vehicle: Dict, task_index: int, offloads: List[Dict]):
        task_id = f"{vehicle['id']}-T{self.sim_time:04d}-{task_index:02d}"
        dag = generate_dag_task(
            task_id=task_id,
            vehicle_id=vehicle["id"],
            sim_time=float(self.sim_time),
            spatial_tag={
                "position": (vehicle["x"], vehicle["y"]),
                "speed_kmh": vehicle["speed_kmh"],
                "heading_deg": vehicle["heading"],
            },
        )

        self._publish_contract_event(
            topic="vehicle_task_submitted",
            event_type="vehicle_task_submitted",
            event_id=f"vehicle_task_submitted:{task_id}",
            payload_obj=VehicleTaskSubmitted(
                task_id=task_id,
                vehicle_id=vehicle["id"],
                sim_time=float(self.sim_time),
                position={"x": float(vehicle["x"]), "y": float(vehicle["y"])},
            ),
        )

        cumulative_latency_ms = 0.0
        task_energy_j = 0.0
        local_handoffs = 0
        pebble_units = []

        for sid in [2, 3, 4, 5]:
            step = dag.steps[sid]

            # Very small steps are executed on the car itself.
            if step.MI <= self.local_step_mi_threshold:
                local_latency_ms, local_energy_j = self._execute_local_step(step)
                cumulative_latency_ms += local_latency_ms
                task_energy_j += local_energy_j
                self.agent_stats["agent1"]["decisions"]["local"] += 1
                self.logic_snapshot["localExec"] += 1
                continue

            ingress_fog = self._nearest_fog(vehicle["x"], vehicle["y"])
            vehicle_hint = self.vehicle_broker.preclassify(step)
            fog_decision = self.fog_broker.decide(step, vehicle_hint=vehicle_hint, ingress_fog=ingress_fog)
            step_class = fog_decision.get("classification", "pebble")
            self._publish_contract_event(
                topic="fog_decision_made",
                event_type="fog_decision_made",
                event_id=f"fog_decision_made:{task_id}:{sid}",
                payload_obj=FogDecisionMade(
                    task_id=task_id,
                    step_id=str(sid),
                    broker_zone=ingress_fog,
                    decision=step_class,
                    destination=fog_decision.get("destination", ingress_fog),
                    reason=fog_decision.get("reason", "none"),
                ),
            )

            # Large step -> cloud directly
            if step_class == "boulder":
                self.agent_stats["agent1"]["decisions"]["cloud"] += 1
                unit_id = f"{task_id}-S{sid}"
                step_latency_ms, step_energy_j = self._execute_remote_unit(
                    vehicle=vehicle,
                    destination="CLOUD",
                    unit_mi=step.MI,
                    unit_in_kb=step.in_KB,
                    unit_id=unit_id,
                    unit_class="boulder",
                    mode="DIRECT",
                    offloads=offloads,
                )
                cumulative_latency_ms += step_latency_ms
                task_energy_j += step_energy_j
            else:
                # Pebble steps must stay in fog tier and may be aggregated later.
                deadline_remaining = max(1.0, TOTAL_DEADLINE_MS - cumulative_latency_ms)
                s1 = self._build_agent1_state(vehicle, step.MI, deadline_remaining)
                a1 = self.agent1.select_action(s1)
                destination = self._destination_from_action(a1)
                if destination == "CLOUD":
                    destination = self._nearest_fog(vehicle["x"], vehicle["y"])

                self.agent_stats["agent1"]["decisions"]["fog"] += 1

                t_exit = self.predictor.compute_t_exit(
                    (vehicle["x"], vehicle["y"]), vehicle["speed_ms"], vehicle["heading"], destination
                )
                if t_exit == float("inf"):
                    t_exit = 10.0
                fog_load = float(np.clip(FOG_NODES[destination].get("load", 0.3) + np.random.uniform(-0.1, 0.1), 0.05, 0.95))
                t_exec = self.predictor.compute_t_exec(step.MI, destination, fog_load)
                mode = self.predictor.select_mode(t_exit, t_exec)

                if mode == "PROACTIVE":
                    next_fog = self.predictor.predict_next_fog(
                        (vehicle["x"], vehicle["y"]), vehicle["speed_ms"], vehicle["heading"], t_exit, destination
                    )
                    if next_fog != "CLOUD":
                        src_fog = destination
                        self._publish_contract_event(
                            topic="handoff_triggered",
                            event_type="handoff_triggered",
                            event_id=f"handoff_triggered:{task_id}:{sid}",
                            payload_obj=HandoffTriggered(
                                task_id=task_id,
                                vehicle_id=vehicle["id"],
                                source_fog=src_fog,
                                target_fog=next_fog,
                                mode="PROACTIVE",
                            ),
                        )
                        src_x, src_y = FOG_NODES[src_fog]["pos"]
                        dst_x, dst_y = FOG_NODES[next_fog]["pos"]
                        offloads.append(
                            {
                                "taskId": f"{task_id}-H{sid}",
                                "vehicleId": vehicle["id"],
                                "from": {"x": float(src_x), "y": float(src_y)},
                                "to": {"x": float(dst_x), "y": float(dst_y), "type": "fog", "id": next_fog},
                                "class": "handoff",
                                "mode": "PROACTIVE",
                                "leg": "fog_to_fog",
                                "network": {"policy": "mobility_handoff", "preinstalled": True, "packetDrop": False, "delayMs": 0.0},
                            }
                        )
                        destination = next_fog
                        self.task_migrations += 1
                        local_handoffs += 1

                pebble_units.append(
                    {
                        "sid": sid,
                        "step": step,
                        "destination": destination,
                        "mode": mode,
                        "s1": s1,
                        "a1": a1,
                    }
                )

        # Aggregate pebble steps into super-tasks by fog destination.
        groups = defaultdict(list)
        for unit in pebble_units:
            groups[unit["destination"]].append(unit)

        for destination, units in groups.items():
            if len(units) >= self.super_task_min_pebbles:
                self.agent_stats["agent1"]["decisions"]["superTasks"] += 1
                self.logic_snapshot["superTasks"] += 1
                super_mi = sum(u["step"].MI for u in units)
                super_in_kb = sum(u["step"].in_KB for u in units)
                super_id = f"{task_id}-SUPER-{destination}"
                super_mode = "PROACTIVE" if any(u["mode"] == "PROACTIVE" for u in units) else "DIRECT"

                step_latency_ms, step_energy_j = self._execute_remote_unit(
                    vehicle=vehicle,
                    destination=destination,
                    unit_mi=super_mi,
                    unit_in_kb=super_in_kb,
                    unit_id=super_id,
                    unit_class="super_pebble",
                    mode=super_mode,
                    offloads=offloads,
                )
                cumulative_latency_ms += step_latency_ms
                task_energy_j += step_energy_j

                for unit in units:
                    deadline_remaining = max(1.0, TOTAL_DEADLINE_MS - cumulative_latency_ms)
                    reward1 = self.agent1.compute_reward(cumulative_latency_ms, task_energy_j, deadline_remaining)
                    ns1 = self._build_agent1_state(vehicle, unit["step"].MI, deadline_remaining)
                    self.agent1.store(unit["s1"], unit["a1"], reward1, ns1, False)
                    self.agent1.update()
                    self._record_agent_reward("agent1", reward1)
                    self._record_agent_update("agent1")
            else:
                for unit in units:
                    unit_id = f"{task_id}-S{unit['sid']}"
                    step_latency_ms, step_energy_j = self._execute_remote_unit(
                        vehicle=vehicle,
                        destination=destination,
                        unit_mi=unit["step"].MI,
                        unit_in_kb=unit["step"].in_KB,
                        unit_id=unit_id,
                        unit_class="pebble",
                        mode=unit["mode"],
                        offloads=offloads,
                    )
                    cumulative_latency_ms += step_latency_ms
                    task_energy_j += step_energy_j

                    deadline_remaining = max(1.0, TOTAL_DEADLINE_MS - cumulative_latency_ms)
                    reward1 = self.agent1.compute_reward(cumulative_latency_ms, task_energy_j, deadline_remaining)
                    ns1 = self._build_agent1_state(vehicle, unit["step"].MI, deadline_remaining)
                    self.agent1.store(unit["s1"], unit["a1"], reward1, ns1, False)
                    self.agent1.update()
                    self._record_agent_reward("agent1", reward1)
                    self._record_agent_update("agent1")

        task_deadline_met = cumulative_latency_ms <= TOTAL_DEADLINE_MS
        self.total_tasks += 1
        if task_deadline_met:
            self.deadline_met_tasks += 1
        self.total_latency_ms += cumulative_latency_ms
        self.total_energy_j += task_energy_j
        self.handoff_count += local_handoffs
        
        # Record metrics in baseline tracker
        destination = None
        if len(offloads) == 0:
            destination = "local"
        elif offloads and "destination" in offloads[-1]:
            destination = offloads[-1]["destination"]
        self.baseline_tracker.record_task_completion(
            latency_ms=cumulative_latency_ms,
            energy_j=task_energy_j,
            deadline_met=task_deadline_met,
            destination=destination
        )
        if local_handoffs > 0:
            self.baseline_tracker.record_handoff()

        # HTB signal for missed deadline due to mobility stress
        if (not task_deadline_met) and local_handoffs > 0:
            self.htb.push(task_id, {"latency_ms": cumulative_latency_ms}, vehicle["id"])

        self._publish_contract_event(
            topic="task_completed",
            event_type="task_completed",
            event_id=f"task_completed:{task_id}",
            payload_obj=TaskCompleted(
                task_id=task_id,
                vehicle_id=vehicle["id"],
                latency_ms=float(cumulative_latency_ms),
                energy_j=float(task_energy_j),
                deadline_met=bool(task_deadline_met),
            ),
        )

    def _flush_store_forward(self):
        """Attempt forwarding of buffered fog-cloud messages when network is healthy."""
        if self.sdn_circuit_breaker.is_open(int(self.sim_time)):
            return

        drained = self.fog_store_forward.drain(limit=15)
        for item in drained:
            flow_id = f"{item.get('taskId', 'unknown')}:retry"
            src = item.get("fromFog", "A")
            payload_kb = float(item.get("payloadKB", 50.0))
            retry_info = self.sdn.route_by_policy(
                flow_id=flow_id,
                source=src,
                destination="CLOUD",
                policy_action=0,
                sim_time=float(self.sim_time),
                payload_kb=payload_kb,
                queue_pressure=float(np.random.uniform(0.1, 0.7)),
            )
            if retry_info.get("packet_drop", False):
                self.sdn_circuit_breaker.on_failure(int(self.sim_time))
                self.fog_store_forward.push(item)
            else:
                self.sdn_circuit_breaker.on_success()

    def _run_simulation_worker(self):
        try:
            print(f"[SIM] Starting simulation ({self.system_type})")
            self.running = True

            while self.sim_time < SIM_DURATION_S and self.running:
                self.sim_time += 1

                vehicles_out = []
                offloads = []

                for vehicle in self.vehicle_states:
                    self._vehicle_move(vehicle)
                    vehicles_out.append(
                        {
                            "id": vehicle["id"],
                            "x": round(vehicle["x"], 2),
                            "y": round(vehicle["y"], 2),
                            "speed": round(vehicle["speed_kmh"], 1),
                        }
                    )

                self._flush_store_forward()

                sampled_idx = np.random.choice(len(self.vehicle_states), size=min(self.tasks_per_second, len(self.vehicle_states)), replace=False)
                for idx_i, vidx in enumerate(sampled_idx):
                    self._simulate_one_dag(self.vehicle_states[int(vidx)], idx_i, offloads)

                # update map state
                self.map_state["vehicles"] = vehicles_out
                self.map_state["offloads"] = offloads
                self.map_state["connections"] = offloads  # connections = all offloads (device->fog, fog->fog, fog->cloud)
                self.map_state["handoffs"] = [o for o in offloads if o.get("class") == "handoff"]  # Filter handoff class
                self.map_state["simulationTime"] = self.sim_time
                
                # Add trajectory predictions for each vehicle
                trajectories = []
                for vehicle in vehicles_out:
                    try:
                        t_exit = self.predictor.compute_t_exit(
                            (vehicle["x"], vehicle["y"]), 
                            vehicle.get("speed_ms", 0),
                            vehicle.get("heading", 0),
                            "A"  # Default to first fog for trajectory calc
                        )
                        if t_exit > 0 and t_exit != float('inf'):
                            next_fog = self.predictor.predict_next_fog(
                                (vehicle["x"], vehicle["y"]),
                                vehicle.get("speed_ms", 0),
                                vehicle.get("heading", 0),
                                t_exit,
                                "A"
                            )
                            waypoints = [
                                {"x": vehicle["x"], "y": vehicle["y"]},
                                {
                                    "x": vehicle["x"] + vehicle.get("speed_ms", 0) * np.cos(np.radians(vehicle.get("heading", 0))) * t_exit,
                                    "y": vehicle["y"] + vehicle.get("speed_ms", 0) * np.sin(np.radians(vehicle.get("heading", 0))) * t_exit
                                }
                            ]
                            trajectories.append({
                                "vehicleId": vehicle["id"],
                                "waypoints": waypoints,
                                "t_exit": float(t_exit),
                                "nextFog": next_fog,
                                "mode": self.predictor.select_mode(t_exit, 0)
                            })
                    except Exception as e:
                        # Skip trajectory if prediction fails
                        pass
                
                self.map_state["trajectories"] = trajectories

                success_rate = (self.deadline_met_tasks / self.total_tasks * 100.0) if self.total_tasks else 0.0
                avg_latency = (self.total_latency_ms / self.total_tasks) if self.total_tasks else 0.0
                throughput = float(len(sampled_idx))

                # pull fog loads from config as dynamic baselines
                fog_loads = {}
                for fog_id in ["A", "B", "C", "D"]:
                    fog_loads[fog_id] = float(np.clip(FOG_NODES[fog_id].get("load", 0.3) + np.random.uniform(-0.12, 0.12), 0.05, 0.95))

                metrics = SystemMetrics(
                    timestamp=datetime.now().isoformat(),
                    simulation_time=float(self.sim_time),
                    success_rate=float(success_rate),
                    avg_latency=float(avg_latency),
                    task_count=int(self.total_tasks),
                    throughput=throughput,
                    fog1_load=fog_loads["A"],
                    fog2_load=fog_loads["B"],
                    fog3_load=fog_loads["C"],
                    fog4_load=fog_loads["D"],
                    cloud_load=float(np.clip(0.2 + self.sdn.get_status()["active_flows"] / 1000.0, 0.1, 0.9)),
                    bandwidth_used=float(np.clip(30 + (self.tasks_per_second / max(1, N_VEHICLES)) * 40 + np.random.uniform(-5, 5), 5, 100)),
                    congestion_points=int(np.clip(np.random.poisson(2), 0, 10)),
                    agent1_latency=float(np.random.uniform(0.6, 2.0)),
                    agent2_latency=float(np.random.uniform(0.4, 1.5)),
                    handoff_count=int(self.handoff_count),
                    task_migrations=int(self.task_migrations),
                    map_snapshot=self.map_state,
                    agent_snapshot=self._build_agent_snapshot(),
                )

                self.logic_snapshot.update(
                    {
                        "simulationTime": self.sim_time,
                        "running": self.running,
                        "systemType": self.system_type,
                        "tasksTotal": self.total_tasks,
                        "deadlineMet": self.deadline_met_tasks,
                        "deadlineRate": success_rate,
                        "avgLatencyMs": avg_latency,
                        "avgEnergyJ": (self.total_energy_j / self.total_tasks) if self.total_tasks else 0.0,
                        "offloadsActive": len(offloads),
                        "handoffs": self.handoff_count,
                        "taskMigrations": self.task_migrations,
                        "sdnReactive": self.sdn.get_status().get("reactive_count", 0),
                        "sdnPreinstallHits": self.sdn.get_status().get("preinstalled_hits", 0),
                        "sdnPacketDrops": self.sdn.get_status().get("packet_drop_count", 0),
                        "relayDeviceToFogMs": (self.relay_device_to_fog_total_ms / self.relay_count) if self.relay_count else 0.0,
                        "relayFogToCloudMs": (self.relay_fog_to_cloud_total_ms / self.relay_count) if self.relay_count else 0.0,
                        "busPublished": self.event_bus.status().get("published", 0),
                        "busDedupDropped": self.event_bus.status().get("dedupDropped", 0),
                        "vehicleBuffer": self.vehicle_store_forward.size(),
                        "fogBuffer": self.fog_store_forward.size(),
                    }
                )

                self.agent_history.append(self._build_agent_snapshot())

                if self.ws_server:
                    self.ws_server.put_metrics(metrics)

                add_metrics(metrics.to_dict())
                update_simulation_time(float(self.sim_time))

                # one simulated second every 100ms wall-clock
                time.sleep(0.1)

            print("[SIM] Completed")
            self.running = False
            self.logic_snapshot["running"] = False
            # Finalize baseline results
            self.baseline_tracker.finalize_run(self.sim_time)
            self._log_event("info", "simulation_completed", total_tasks=self.total_tasks)
        except Exception as e:
            print(f"[SIM] Error: {e}")
            self.running = False
            self.logic_snapshot["running"] = False
            self._log_event("error", "simulation_failed", error=str(e))

    def start(self):
        # Start websocket
        self._initialize_websocket()
        self.ws_server.run_in_thread()
        time.sleep(1)

        # Start API
        api_thread = threading.Thread(
            target=lambda: self.flask_app.run(
                host="127.0.0.1",
                port=5000,
                debug=False,
                threaded=True,
                use_reloader=False,
            ),
            daemon=True,
        )
        api_thread.start()
        time.sleep(1)

        # Optional offline behavioral cloning bootstrap before live simulation.
        # Run this after API/WS start so the dashboard can connect immediately.
        self._bootstrap_behavioral_cloning()

        # Start simulation
        self._api_start_simulation(self.system_type)

        print("=" * 80)
        print("[API]       http://127.0.0.1:5000")
        print("[HEALTH]    http://127.0.0.1:5000/api/health")
        print("[MAP API]   http://127.0.0.1:5000/api/map/live")
        print("[WS]        ws://127.0.0.1:8765")
        print("[DASHBOARD] http://localhost:3000")
        print("[MAP VIEW]  http://localhost:3000/map")
        print("=" * 80)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            sys.exit(0)


def main():
    system_type = sys.argv[1] if len(sys.argv) > 1 else "proposed"
    valid = ["baseline1", "baseline2", "baseline3", "proposed"]
    if system_type not in valid:
        print(f"Invalid system type. Choose from: {', '.join(valid)}")
        sys.exit(1)

    app = UnifiedSmartCityApp(system_type=system_type)
    app.start()


if __name__ == "__main__":
    main()
