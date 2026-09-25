"""
Fog Service - Runs fog nodes, Agent2 (routing), SDN controller, authoritative TOF.
Connects vehicles and cloud via NATS with mTLS.

Run: python -m services.fog_service
"""

import asyncio
import time
import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass

from config import (
    FOG_NODES, FOG_MIPS, FOG_COVERAGE_RADIUS, EC_THRESHOLD,
    SIM_DURATION_S, WARMUP_S, RANDOM_SEED
)
from agents.agent2 import Agent2
from broker.tof_roles import TofFogBroker
from sdn.controller import SDNController
from framework.contracts import FogDecisionMade, CloudForwarded, make_envelope
from infrastructure.nats_bus import NatsServiceBus, NatsEventBridge, NatsMessage
from results.logging_utils import setup_application_logger


@dataclass
class FogNodeState:
    id: str
    name: str
    x: float
    y: float
    load: float
    queue_length: int


class FogService:
    """Fog-side service: fog nodes, Agent2, SDN, authoritative TOF."""

    def __init__(self, nats_url: str = "nats://localhost:4222", cert_dir: str = "certs"):
        self.nats_url = nats_url
        self.cert_dir = cert_dir

        # NATS messaging
        self.nats_bus = NatsServiceBus(
            service_name="fog-service",
            nats_url=nats_url,
            cert_dir=cert_dir,
            enable_tls=True
        )
        self.event_bridge = NatsEventBridge(self.nats_bus)

        # Agent2 for routing decisions
        self.agent2 = Agent2()

        # Fog-side authoritative TOF classifier
        self.fog_broker = TofFogBroker(threshold=EC_THRESHOLD, fog_mips=FOG_MIPS)

        # SDN controller for path optimization
        self.sdn = SDNController()

        # Fog node states
        self.fog_nodes: Dict[str, FogNodeState] = {}
        self._initialize_fog_nodes()

        # Task queue for processing
        self.task_queue: Dict[str, dict] = {}

        # Simulation state
        self.sim_time = 0.0
        self.running = False

        self.logger = setup_application_logger("fog_service", "results/logs")

    def _initialize_fog_nodes(self):
        """Initialize fog node states."""
        np.random.seed(RANDOM_SEED)
        for fog_id, fog_config in FOG_NODES.items():
            self.fog_nodes[fog_id] = FogNodeState(
                id=fog_id,
                name=fog_config.get("name", f"Fog-{fog_id}"),
                x=float(fog_config["pos"][0]),
                y=float(fog_config["pos"][1]),
                load=float(fog_config.get("load", 0.3)),
                queue_length=0
            )
        print(f"[F-SVC] Initialized {len(self.fog_nodes)} fog nodes")

    async def _handle_vehicle_task(self, msg: NatsMessage):
        """Handle incoming vehicle task submission."""
        payload = msg.payload
        task_id = payload.get("task_id")
        vehicle_id = payload.get("vehicle_id")
        x = payload.get("position_x", 500)
        y = payload.get("position_y", 500)

        print(f"[F-SVC] Received task {task_id} from {vehicle_id}")

        # Find nearest fog node
        nearest_fog = self._find_nearest_fog(x, y)
        if not nearest_fog:
            # No fog in range, mark for cloud
            decision = "cloud"
        else:
            # Check load with Agent2 routing decision
            fog_state = self.fog_nodes[nearest_fog]
            decision = "fog" if fog_state.load < 0.7 else "cloud"

            # Update fog queue
            fog_state.queue_length += 1

        # Publish decision
        decision_payload = {
            "task_id": task_id,
            "vehicle_id": vehicle_id,
            "decision": decision,
            "target_fog": nearest_fog if decision == "fog" else None,
            "timestamp_s": self.sim_time,
        }

        await self.event_bridge.publish_event(
            "FogDecisionMade",
            decision_payload,
            target_service="vehicle-service" if decision == "fog" else "cloud-service"
        )

        self.task_queue[task_id] = decision_payload

    def _find_nearest_fog(self, x: float, y: float) -> Optional[str]:
        """Find nearest fog node within coverage radius."""
        min_dist = float('inf')
        nearest = None

        for fog_id, fog in self.fog_nodes.items():
            dist = np.sqrt((x - fog.x) ** 2 + (y - fog.y) ** 2)
            if dist <= FOG_COVERAGE_RADIUS and dist < min_dist:
                min_dist = dist
                nearest = fog_id

        return nearest

    async def _run_maintenance_loop(self):
        """Periodic maintenance: update loads, drain queues."""
        while self.running:
            self.sim_time = time.time()

            # Update fog loads based on queue
            for fog_id, fog in self.fog_nodes.items():
                # Decay queue over time (simulating processing)
                fog.queue_length = max(0, fog.queue_length - int(FOG_MIPS / 1000 * 0.1))
                fog.load = min(1.0, fog.queue_length / 50.0)

            await asyncio.sleep(1.0)

    async def start(self):
        """Start the fog service."""
        print("[F-SVC] Starting fog service...")
        await self.nats_bus.connect()

        # Subscribe to vehicle task submissions
        await self.nats_bus.subscribe(
            "telemetry.vehicle.task-submitted",
            self._handle_vehicle_task,
            queue_group="fog-service"
        )

        # Start maintenance
        self.running = True
        tasks = [
            asyncio.create_task(self._run_maintenance_loop()),
        ]

        # Wait for all tasks
        await asyncio.gather(*tasks)

    async def stop(self):
        """Stop the service gracefully."""
        print("[F-SVC] Stopping...")
        self.running = False
        await self.nats_bus.disconnect()


async def main():
    service = FogService()
    try:
        await service.start()
    except KeyboardInterrupt:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
