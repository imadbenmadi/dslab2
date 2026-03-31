"""
Vehicle Service - Runs vehicles with Agent1 (task placement).
Connects to Fog Service via NATS with mTLS.

Run: python -m services.vehicle_service
"""

import asyncio
import sys
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from config import (
    N_VEHICLES, VEHICLE_SPEED_MEAN, VEHICLE_SPEED_STD,
    TASK_RATE_HZ, FOG_COVERAGE_RADIUS, N_VEHICLES, RANDOM_SEED,
    SIM_DURATION_S, WARMUP_S
)
from agents.agent1 import Agent1
from broker.tof_roles import TofLiteVehicleBroker
from environment.task import generate_dag_task
from framework.contracts import VehicleTaskSubmitted, make_envelope
from infrastructure.nats_bus import NatsServiceBus, NatsEventBridge
from infrastructure.cert_manager import get_mtls_config
from datasets import TrajectoryGenerator
import csv


@dataclass
class VehicleState:
    id: str
    x: float
    y: float
    speed_kmh: float
    heading_deg: float
    timestamp_s: float


class VehicleService:
    """Vehicle-side service: runs vehicles, Agent1, and vehicle-side TOF."""

    def __init__(self, nats_url: str = "nats://localhost:4222", cert_dir: str = "certs"):
        self.nats_url = nats_url
        self.cert_dir = cert_dir

        # NATS messaging
        self.nats_bus = NatsServiceBus(
            service_name="vehicle-service",
            nats_url=nats_url,
            cert_dir=cert_dir,
            enable_tls=True
        )
        self.event_bridge = NatsEventBridge(self.nats_bus)

        # Vehicle agent
        self.agent1 = Agent1()

        # Vehicle-side TOF classifier
        self.vehicle_broker = TofLiteVehicleBroker(threshold=1.0, fog_mips=2000)

        # Vehicle trajectories
        self.trajectory_gen = TrajectoryGenerator(profile="urban")
        self.vehicle_states: List[VehicleState] = []
        self._initialize_vehicles()

        # Simulation state
        self.sim_time = 0.0
        self.running = False
        self.task_counter = 0

    def _initialize_vehicles(self):
        """Initialize vehicle positions and velocities."""
        np.random.seed(RANDOM_SEED)
        for i in range(N_VEHICLES):
            x = np.random.uniform(50, 950)
            y = np.random.uniform(50, 950)
            speed = np.random.normal(VEHICLE_SPEED_MEAN, VEHICLE_SPEED_STD)
            speed = max(10, min(speed, 140))
            heading = np.random.uniform(0, 360)

            self.vehicle_states.append(VehicleState(
                id=f"V{i:03d}",
                x=float(x),
                y=float(y),
                speed_kmh=float(speed),
                heading_deg=float(heading),
                timestamp_s=0.0
            ))
        print(f"[V-SVC] Initialized {N_VEHICLES} vehicles")

    async def _run_simulation_loop(self):
        """Main simulation loop: move vehicles, generate tasks."""
        start_time = time.time()

        while self.running and (time.time() - start_time) < SIM_DURATION_S:
            # Advance time
            self.sim_time = time.time() - start_time

            # Skip warmup
            if self.sim_time < WARMUP_S:
                await asyncio.sleep(0.1)
                continue

            # Move vehicles
            for vehicle in self.vehicle_states:
                heading_rad = np.radians(vehicle.heading_deg)
                vehicle.x += vehicle.speed_kmh * (1000.0 / 3600.0) * 0.1 * np.cos(heading_rad) / 1000.0
                vehicle.y += vehicle.speed_kmh * (1000.0 / 3600.0) * 0.1 * np.sin(heading_rad) / 1000.0

                # Reflect at boundaries
                if vehicle.x < 50 or vehicle.x > 950:
                    vehicle.heading_deg = (180.0 - vehicle.heading_deg) % 360.0
                    vehicle.x = max(50, min(vehicle.x, 950))
                if vehicle.y < 50 or vehicle.y > 950:
                    vehicle.heading_deg = (-vehicle.heading_deg) % 360.0
                    vehicle.y = max(50, min(vehicle.y, 950))

                vehicle.timestamp_s = self.sim_time

            # Generate tasks from vehicles (at TASK_RATE_HZ)
            tasks_per_step = int(N_VEHICLES * TASK_RATE_HZ * 0.1)
            for _ in range(max(1, tasks_per_step)):
                vid = np.random.randint(0, N_VEHICLES)
                vehicle = self.vehicle_states[vid]

                # Generate task
                task = generate_dag_task(
                    task_id=f"T-{self.task_counter:08d}",
                    vehicle_id=vehicle.id,
                    sim_time=self.sim_time,
                    spatial_tag={
                        "position": (vehicle.x, vehicle.y),
                        "speed_kmh": vehicle.speed_kmh,
                        "heading_deg": vehicle.heading_deg,
                    }
                )

                # Classify with vehicle-side TOF
                local_exec = self.vehicle_broker.classify(task)

                # Build contract event
                event_payload = {
                    "vehicle_id": vehicle.id,
                    "task_id": task.task_id,
                    "classification": "local" if local_exec else "offload",
                    "position_x": vehicle.x,
                    "position_y": vehicle.y,
                    "timestamp_s": self.sim_time,
                }

                # Publish to NATS (target: fog-service for decision)
                await self.event_bridge.publish_event(
                    "VehicleTaskSubmitted",
                    event_payload,
                    target_service="fog-service"
                )

                self.task_counter += 1

            await asyncio.sleep(0.1)  # 10 Hz loop

        print(f"[V-SVC] Simulation loop ended at t={self.sim_time}s")

    async def start(self):
        """Start the vehicle service."""
        print("[V-SVC] Starting vehicle service...")
        await self.nats_bus.connect()

        # Subscribe to fog decisions (for Agent1 reward signal)
        async def handle_fog_decision(msg):
            # Could use this for online reward feedback to Agent1
            print(f"[V-SVC] Received fog decision: {msg.id}")

        await self.nats_bus.subscribe(
            "telemetry.fog.decision",
            handle_fog_decision,
            queue_group="vehicle-service"
        )

        self.running = True
        await self._run_simulation_loop()

    async def stop(self):
        """Stop the service gracefully."""
        print("[V-SVC] Stopping...")
        self.running = False
        await self.nats_bus.disconnect()


async def main():
    service = VehicleService()
    try:
        await service.start()
    except KeyboardInterrupt:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
