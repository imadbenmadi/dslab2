from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from pcnme.core.config import Settings
from pcnme.core.topology import Topology
from pcnme.datasets.synthetic import SyntheticGenerator
from pcnme.broker.tof_broker import TOFBroker
from pcnme.core.enums import TaskClass
from pcnme.core.task import DAGStep
from pcnme.agents.features import build_agent1_state, build_agent2_state
from pcnme.optimizer.problem import OffloadingUnit, TaskOffloadingProblem
from pcnme.sdn.controller import SDNController
from pcnme.simulation.models import FogRuntimeState, MetricsSummary, SimulationSnapshot, VehicleState
from pcnme.storage.redis_store import RedisStore


@dataclass
class EngineStatus:
    running: bool
    sim_time_s: float


class SimulationEngine:
    """Asyncio simulation loop publishing state + metrics to Redis."""

    def __init__(self, *, settings: Settings, topology: Topology, store: RedisStore):
        self.settings = settings
        self.topology = topology
        self.store = store

        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._lock = asyncio.Lock()

        self.sim_time_s = 0.0
        self.rng = np.random.default_rng(int(settings.RANDOM_SEED))
        self.metrics = MetricsSummary()

        self._vehicles: List[VehicleState] = []
        self._fog_queue: Dict[str, int] = {f.id: 0 for f in topology.iter_fogs()}
        self._fog_load: Dict[str, float] = {f.id: float(np.clip(f.initial_load, 0.05, 0.95)) for f in topology.iter_fogs()}
        self._sdn = SDNController(settings=settings)
        self._tof = TOFBroker(fog_mips=int(settings.FOG_MIPS), threshold_s=float(settings.EC_THRESHOLD))
        self._gen = SyntheticGenerator(settings=settings, topology=topology, rng=self.rng)

        self._agent1 = self._try_load_dqn(settings.AGENT1_MODEL_PATH, default_rel_path=Path("results") / "agent1.pt")
        self._agent2 = self._try_load_dqn(settings.AGENT2_MODEL_PATH, default_rel_path=Path("results") / "agent2.pt")

        self._init_vehicles()

    def _try_load_dqn(self, path: Optional[str], *, default_rel_path: Path):
        model_path = Path(path) if path else default_rel_path
        if not model_path.exists():
            return None
        try:
            from pcnme.agents.dqn import DQNAgent

            agent = DQNAgent.load(str(model_path))
            agent.q.eval()
            return agent
        except Exception:
            return None

    def _init_vehicles(self) -> None:
        self._vehicles = []
        fogs = list(self.topology.iter_fogs())
        for i in range(int(self.settings.N_VEHICLES)):
            fog = self.rng.choice(fogs)
            angle = float(self.rng.uniform(0.0, 2.0 * math.pi))
            radius = float(self.rng.uniform(0.0, self.topology.fog_coverage_radius_m * 0.9))
            x = float(fog.pos.x + radius * math.cos(angle))
            y = float(fog.pos.y + radius * math.sin(angle))
            speed_kmh = float(max(5.0, self.rng.normal(self.settings.VEHICLE_SPEED_MEAN, self.settings.VEHICLE_SPEED_STD)))
            speed_ms = speed_kmh / 3.6
            heading = float(self.rng.uniform(0.0, 360.0))
            self._vehicles.append(VehicleState(id=f"veh{i:03d}", x=x, y=y, speed_ms=speed_ms, heading_deg=heading))

    async def start(self) -> None:
        async with self._lock:
            if self._task and not self._task.done():
                return
            self._stop.clear()
            self._task = asyncio.create_task(self._run_loop(), name="pcnme-sim")
            # Publish an initial snapshot immediately.
            await self.store.set_latest_state(self.snapshot().to_dict())

    async def stop(self) -> None:
        async with self._lock:
            self._stop.set()
            if self._task:
                await self._task
            self._task = None

    def status(self) -> EngineStatus:
        running = self._task is not None and not self._task.done()
        return EngineStatus(running=bool(running), sim_time_s=float(self.sim_time_s))

    def snapshot(self) -> SimulationSnapshot:
        fogs = [
            FogRuntimeState(
                id=f.id,
                x=float(f.pos.x),
                y=float(f.pos.y),
                load=float(self._fog_load[f.id]),
                queue_depth=int(self._fog_queue[f.id]),
            )
            for f in self.topology.iter_fogs()
        ]
        return SimulationSnapshot(sim_time_s=float(self.sim_time_s), vehicles=list(self._vehicles), fogs=fogs, metrics=self.metrics)

    async def _run_loop(self) -> None:
        dt = 0.5
        duration = float(self.settings.SIM_DURATION_S)
        while not self._stop.is_set() and self.sim_time_s < duration:
            self._tick(dt)
            await self.store.set_latest_state(self.snapshot().to_dict())
            await asyncio.sleep(0)

    def _tick(self, dt: float) -> None:
        self.sim_time_s += float(dt)
        self._update_mobility(dt)
        self._update_connectivity()
        self._generate_and_process_tasks(dt)
        self._decay_queues(dt)

    def _update_mobility(self, dt: float) -> None:
        # Bounded random movement around the convex hull of fog nodes.
        fogs = list(self.topology.iter_fogs())
        min_x = min(f.pos.x for f in fogs) - self.topology.fog_coverage_radius_m
        max_x = max(f.pos.x for f in fogs) + self.topology.fog_coverage_radius_m
        min_y = min(f.pos.y for f in fogs) - self.topology.fog_coverage_radius_m
        max_y = max(f.pos.y for f in fogs) + self.topology.fog_coverage_radius_m

        for v in self._vehicles:
            v.heading_deg = float((v.heading_deg + self.rng.normal(0.0, 6.0)) % 360.0)
            heading = math.radians(v.heading_deg)
            v.x += float(v.speed_ms * math.cos(heading) * dt)
            v.y += float(v.speed_ms * math.sin(heading) * dt)

            # Reflect at bounds
            if v.x < min_x:
                v.x = min_x + (min_x - v.x)
                v.heading_deg = float((180.0 - v.heading_deg) % 360.0)
            elif v.x > max_x:
                v.x = max_x - (v.x - max_x)
                v.heading_deg = float((180.0 - v.heading_deg) % 360.0)
            if v.y < min_y:
                v.y = min_y + (min_y - v.y)
                v.heading_deg = float((-v.heading_deg) % 360.0)
            elif v.y > max_y:
                v.y = max_y - (v.y - max_y)
                v.heading_deg = float((-v.heading_deg) % 360.0)

    def _update_connectivity(self) -> None:
        for v in self._vehicles:
            fog_id, _ = self.topology.nearest_fog_in_range(v.x, v.y)
            v.connected_fog_id = fog_id

    def _generate_and_process_tasks(self, dt: float) -> None:
        # Generate pebble-like tasks stochastically.
        p = float(self.settings.TASK_RATE_HZ) * float(dt)
        for v in self._vehicles:
            if v.connected_fog_id is None:
                continue
            if self.rng.random() > p:
                continue

            # Create one unit per event
            unit = OffloadingUnit(
                unit_id=f"t@{self.sim_time_s:.1f}:{v.id}",
                mi=float(self.rng.uniform(60.0, float(self.settings.FOG_MIPS) * float(self.settings.EC_THRESHOLD) * 0.95)),
                in_kb=float(self.rng.uniform(5.0, 200.0)),
                out_kb=float(self.rng.uniform(1.0, 60.0)),
                vehicle_xy=(float(v.x), float(v.y)),
                ingress_fog_id=str(v.connected_fog_id),
                deadline_ms=float(self.rng.uniform(80.0, 220.0)),
            )

            decision = self._tof.decide(DAGStep(id=0, name="step", MI=float(unit.mi), in_KB=float(unit.in_kb), out_KB=float(unit.out_kb)))

            fog_ids = self.topology.fog_ids()
            fog_loads = dict(self._fog_load)

            # Placement policy:
            # - boulder => force CLOUD
            # - pebble  => Agent1 if available, else least-loaded fog
            if decision.classification == TaskClass.BOULDER:
                best_action = len(fog_ids)  # cloud index
            elif self._agent1 is not None:
                s = build_agent1_state(unit=unit, settings=self.settings, topology=self.topology, fog_loads=fog_loads)
                best_action = int(self._agent1.act(s, epsilon=0.0))
            else:
                least_loaded = min(fog_ids, key=lambda fid: float(fog_loads.get(fid, 0.5)))
                best_action = fog_ids.index(least_loaded)

            if best_action >= len(fog_ids):
                best_fog = "CLOUD"
            else:
                best_fog = str(fog_ids[int(best_action)])

            # Evaluate (latency_ms, energy)
            problem = TaskOffloadingProblem(settings=self.settings, topology=self.topology, units=[unit], fog_loads=fog_loads)
            out = {}
            problem._evaluate(np.array([[best_action]], dtype=int), out)
            latency_ms, energy = [float(x) for x in out["F"][0]]

            # SDN routing if forwarding to non-ingress fog / cloud
            packet_drop = False
            if best_fog == "CLOUD":
                preinstall_hit = self._sdn.cache.has(src=str(v.connected_fog_id), dst="CLOUD")
                if self._agent2 is not None:
                    s2 = build_agent2_state(
                        queue_pressure=float(self._fog_load[str(v.connected_fog_id)]),
                        payload_kb=float(unit.in_kb),
                        destination_is_cloud=True,
                        preinstall_hit=bool(preinstall_hit),
                        settings=self.settings,
                    )
                    policy_action = int(self._agent2.act(s2, epsilon=0.0))
                else:
                    policy_action = 0
                route = self._sdn.route_by_policy(
                    flow_id=unit.unit_id,
                    source=str(v.connected_fog_id),
                    destination="CLOUD",
                    policy_action=policy_action,
                    queue_pressure=float(self._fog_load[str(v.connected_fog_id)]),
                    payload_kb=float(unit.in_kb),
                    sim_time_s=float(self.sim_time_s),
                )
                latency_ms += float(route.total_delay_ms)
                packet_drop = bool(route.packet_drop)
                self.metrics.update(latency_ms=latency_ms, energy=energy, to_cloud=True, packet_drop=packet_drop)
            elif best_fog != v.connected_fog_id:
                preinstall_hit = self._sdn.cache.has(src=str(v.connected_fog_id), dst=str(best_fog))
                if self._agent2 is not None:
                    s2 = build_agent2_state(
                        queue_pressure=float(self._fog_load[str(v.connected_fog_id)]),
                        payload_kb=float(unit.in_kb),
                        destination_is_cloud=False,
                        preinstall_hit=bool(preinstall_hit),
                        settings=self.settings,
                    )
                    policy_action = int(self._agent2.act(s2, epsilon=0.0))
                else:
                    policy_action = 0
                route = self._sdn.route_by_policy(
                    flow_id=unit.unit_id,
                    source=str(v.connected_fog_id),
                    destination=str(best_fog),
                    policy_action=policy_action,
                    queue_pressure=float(self._fog_load[str(v.connected_fog_id)]),
                    payload_kb=float(unit.in_kb),
                    sim_time_s=float(self.sim_time_s),
                )
                latency_ms += float(route.total_delay_ms)
                packet_drop = bool(route.packet_drop)
                self.metrics.update(latency_ms=latency_ms, energy=energy, to_cloud=False, packet_drop=packet_drop)
                self._fog_queue[str(best_fog)] += 1
                self._fog_load[str(best_fog)] = float(np.clip(self._fog_queue[str(best_fog)] / max(self.settings.Q_MAX, 1), 0.05, 0.95))
            else:
                self.metrics.update(latency_ms=latency_ms, energy=energy, to_cloud=False, packet_drop=packet_drop)
                self._fog_queue[str(best_fog)] += 1
                self._fog_load[str(best_fog)] = float(np.clip(self._fog_queue[str(best_fog)] / max(self.settings.Q_MAX, 1), 0.05, 0.95))

            # Persist metric event
            asyncio.create_task(
                self.store.append_metric(
                    {
                        "type": "task",
                        "sim_time_s": float(self.sim_time_s),
                        "vehicle_id": v.id,
                        "ingress_fog": str(v.connected_fog_id),
                        "target": str(best_fog),
                        "latency_ms": float(latency_ms),
                        "energy": float(energy),
                        "packet_drop": bool(packet_drop),
                        "class": decision.classification.value,
                    }
                )
            )

    def _decay_queues(self, dt: float) -> None:
        # Simulate service by draining queues.
        drain = max(1, int(2.0 * dt))
        for fog_id in list(self._fog_queue.keys()):
            self._fog_queue[fog_id] = max(0, int(self._fog_queue[fog_id]) - drain)
            self._fog_load[fog_id] = float(np.clip(self._fog_queue[fog_id] / max(self.settings.Q_MAX, 1), 0.05, 0.95))
