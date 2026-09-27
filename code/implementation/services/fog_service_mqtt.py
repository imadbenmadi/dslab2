"""
MQTT-enabled Fog Service.
Handles fog node orchestration and routing decisions with Agent2.

Run: python -m services.fog_service_mqtt
"""

import asyncio
import os
import sys
from pathlib import Path
from collections import defaultdict

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from environment.fog_node import FogNode
from agents.agent2 import Agent2
from infrastructure.mqtt_bus import MQTTServiceBus, MQTTEventBridge, MQTTQoS
from infrastructure.pki_manager import PKIManager
from framework.contracts import (
    FogDecisionMade,
    HandoffTriggered,
)


class FogServiceMQTT:
    """Fog service using MQTT messaging."""

    def __init__(
        self,
        mqtt_host: str = None,
        mqtt_port: int = None,
        cert_dir: str = "certs"
    ):
        self.mqtt_host = mqtt_host or os.getenv("MQTT_HOST", "localhost")
        self.mqtt_port = mqtt_port or int(os.getenv("MQTT_PORT", 8883))
        self.cert_dir = cert_dir

        self.fog_nodes = {}
        self.vehicle_to_fog = {}  # Track which vehicle is associated with which fog
        self.mqtt_bus = None
        self.mqtt_bridge = None
        self.pki_manager = None

    async def setup(self) -> bool:
        """Initialize MQTT connection and PKI."""
        print(f"[FOG-MQTT] Setting up fog service...")
        print(f"  MQTT broker: {self.mqtt_host}:{self.mqtt_port}")
        print(f"  Cert dir: {self.cert_dir}")

        try:
            # Initialize PKI
            self.pki_manager = PKIManager(
                root_cert_path=f"{self.cert_dir}/root-ca.crt",
                root_key_path=f"{self.cert_dir}/root-ca.key"
            )

            # Create MQTT bus
            self.mqtt_bus = MQTTServiceBus(
                service_name="fog-service",
                broker_host=self.mqtt_host,
                broker_port=self.mqtt_port,
                cert_dir=self.cert_dir,
                enable_tls=True,
                qos=MQTTQoS.AT_LEAST_ONCE
            )

            # Create event bridge
            self.mqtt_bridge = MQTTEventBridge(self.mqtt_bus)

            # Connect to MQTT
            if not self.mqtt_bus.connect():
                print("[FOG-MQTT] Failed to connect to MQTT broker")
                return False

            # Subscribe to vehicle online events
            self.mqtt_bus.subscribe(
                "vehicle/online",
                self._on_vehicle_online,
                qos=MQTTQoS.AT_LEAST_ONCE.value
            )

            # Subscribe to task completion events
            self.mqtt_bus.subscribe(
                "task/completed",
                self._on_task_completed,
                qos=MQTTQoS.AT_LEAST_ONCE.value
            )

            print("[FOG-MQTT] Setup complete")
            return True

        except Exception as e:
            print(f"[FOG-MQTT] Setup error: {e}")
            return False

    async def create_fog_node(
        self,
        fog_id: str,
        location: tuple = (35.1264, 33.4299),
        capacity: int = 100
    ) -> FogNode:
        """Create and initialize a fog node with Agent2."""
        print(f"[FOG-MQTT] Creating fog node {fog_id}...")

        fog_node = FogNode(
            fog_id=fog_id,
            location=location,
            compute_capacity=capacity
        )

        # Attach Agent2 (routing decision maker)
        agent = Agent2(agent_id=f"agent2-{fog_id}")
        fog_node.set_agent(agent)

        self.fog_nodes[fog_id] = {
            "fog": fog_node,
            "agent": agent,
            "vehicle_queue": defaultdict(list),
            "decisions_made": 0,
        }

        return fog_node

    async def _on_vehicle_online(self, msg):
        """Handle vehicle coming online."""
        try:
            event_data = msg.payload
            vehicle_id = event_data.get("vehicle_id")

            # Assign vehicle to nearest fog node
            fog_id = self._select_fog_node(vehicle_id)

            self.vehicle_to_fog[vehicle_id] = fog_id

            print(f"[FOG-MQTT] Vehicle {vehicle_id} assigned to fog {fog_id}")

        except Exception as e:
            print(f"[FOG-MQTT] Vehicle online error: {e}")

    async def _on_task_completed(self, msg):
        """Handle task completion from vehicle."""
        try:
            task_data = msg.payload
            vehicle_id = task_data.get("vehicle_id")

            # Retrieve fog node for this vehicle
            fog_id = self.vehicle_to_fog.get(vehicle_id)

            if not fog_id:
                print(f"[FOG-MQTT] No fog node associated with {vehicle_id}")
                return

            fog_info = self.fog_nodes.get(fog_id)
            if not fog_info:
                return

            print(f"[FOG-MQTT] Task from {vehicle_id} → {fog_id}")

            # Store in vehicle queue
            fog_info["vehicle_queue"][vehicle_id].append(task_data)

        except Exception as e:
            print(f"[FOG-MQTT] Task completion error: {e}")

    def _select_fog_node(self, vehicle_id: str) -> str:
        """Select best fog node for vehicle (simple round-robin)."""
        if not self.fog_nodes:
            return None

        # Simple strategy: pick the first available
        fog_ids = list(self.fog_nodes.keys())
        return fog_ids[0] if fog_ids else None

    async def process_routing_decisions(self):
        """Main routing decision loop."""
        print("[FOG-MQTT] Starting routing decisions...")

        while True:
            try:
                # Process each fog node
                for fog_id, fog_info in self.fog_nodes.items():
                    fog = fog_info["fog"]
                    agent = fog_info["agent"]

                    # Check for queued tasks
                    for vehicle_id, tasks in fog_info["vehicle_queue"].items():
                        if not tasks:
                            continue

                        # Get next task
                        task = tasks.pop(0)

                        # Use Agent2 to decide: execute at fog or forward to cloud
                        decision = agent.decide_routing(task, fog)

                        print(f"[FOG-MQTT] {fog_id} routing decision for {vehicle_id}: {decision}")

                        # Publish decision
                        decision_event = {
                            "fog_id": fog_id,
                            "vehicle_id": vehicle_id,
                            "task_id": task.get("task_id"),
                            "routing_decision": decision,
                            "timestamp_s": asyncio.get_event_loop().time()
                        }

                        msg_id = self.mqtt_bridge.publish_event(
                            "FogDecisionMade",
                            decision_event,
                            target_service="cloud-service" if decision == "cloud" else None,
                            qos=MQTTQoS.AT_LEAST_ONCE
                        )

                        fog_info["decisions_made"] += 1
                        print(f"[FOG-MQTT] Decision published: {msg_id}")

                await asyncio.sleep(1)

            except Exception as e:
                print(f"[FOG-MQTT] Routing error: {e}")
                await asyncio.sleep(1)

    async def run(self):
        """Run the fog service."""
        if not await self.setup():
            print("[FOG-MQTT] Setup failed")
            return

        # Create a few fog nodes
        for i in range(2):
            fog_id = f"fog-{i:03d}"
            await self.create_fog_node(fog_id)

        # Run routing decisions
        await self.process_routing_decisions()

    def stop(self):
        """Stop the service."""
        print("[FOG-MQTT] Stopping...")
        if self.mqtt_bus:
            self.mqtt_bus.disconnect()
        print("[FOG-MQTT] Stopped")


async def main():
    """Entry point."""
    service = FogServiceMQTT()

    try:
        await service.run()
    except KeyboardInterrupt:
        print("\n[FOG-MQTT] Interrupted")
        service.stop()


if __name__ == "__main__":
    asyncio.run(main())
