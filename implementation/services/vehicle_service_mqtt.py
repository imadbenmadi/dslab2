"""
MQTT-enabled Vehicle Service.
Replaces NATS with MQTT messaging.

Run: python -m services.vehicle_service_mqtt
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from environment.vehicle import Vehicle
from agents.agent1 import Agent1
from infrastructure.mqtt_bus import MQTTServiceBus, MQTTEventBridge, MQTTQoS
from infrastructure.mqtt_pki_integration import MQTTServiceProvisioner
from infrastructure.pki_manager import PKIManager
from framework.contracts import (
    VehicleTaskSubmitted,
    VehicleTaskAck,
    HandoffTriggered,
    TaskCompleted,
)


class VehicleServiceMQTT:
    """Vehicle service using MQTT messaging."""

    def __init__(
        self,
        mqtt_host: str = None,
        mqtt_port: int = None,
        cert_dir: str = "certs"
    ):
        self.mqtt_host = mqtt_host or os.getenv("MQTT_HOST", "localhost")
        self.mqtt_port = mqtt_port or int(os.getenv("MQTT_PORT", 8883))
        self.cert_dir = cert_dir

        self.vehicles = {}
        self.mqtt_bus = None
        self.mqtt_bridge = None
        self.pki_manager = None

    async def setup(self) -> bool:
        """Initialize MQTT connection and PKI."""
        print(f"[VEHICLE-MQTT] Setting up vehicle service...")
        print(f"  MQTT broker: {self.mqtt_host}:{self.mqtt_port}")
        print(f"  Cert dir: {self.cert_dir}")

        try:
            # Initialize PKI
            self.pki_manager = PKIManager(
                root_cert_path=f"{self.cert_dir}/root-ca.crt",
                root_key_path=f"{self.cert_dir}/root-ca.key"
            )

            # Create MQTT bus with certificates
            self.mqtt_bus = MQTTServiceBus(
                service_name="vehicle-service",
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
                print("[VEHICLE-MQTT] Failed to connect to MQTT broker")
                return False

            # Subscribe to incoming tasks
            self.mqtt_bus.subscribe(
                "vehicle/task-submit",
                self._on_task_received,
                qos=MQTTQoS.AT_LEAST_ONCE.value
            )

            # Subscribe to handoff events
            self.mqtt_bus.subscribe(
                "mobility/handoff",
                self._on_handoff,
                qos=MQTTQoS.AT_LEAST_ONCE.value
            )

            print("[VEHICLE-MQTT] Setup complete")
            return True

        except Exception as e:
            print(f"[VEHICLE-MQTT] Setup error: {e}")
            return False

    async def create_vehicle(
        self,
        vehicle_id: str,
        vehicle_type: str = "sedan",
        initial_lat: float = 35.1264,
        initial_lon: float = 33.4299
    ) -> Vehicle:
        """Create and initialize a vehicle with Agent1."""
        print(f"[VEHICLE-MQTT] Creating vehicle {vehicle_id}...")

        vehicle = Vehicle(
            vehicle_id=vehicle_id,
            vehicle_type=vehicle_type,
            initial_location=(initial_lat, initial_lon)
        )

        # Attach Agent1 (DQN decision maker)
        agent = Agent1(agent_id=f"agent1-{vehicle_id}")
        vehicle.set_agent(agent)

        self.vehicles[vehicle_id] = {
            "vehicle": vehicle,
            "agent": agent,
            "tasks_received": 0,
            "tasks_completed": 0,
        }

        # Publish vehicle online event
        await self._publish_vehicle_online(vehicle_id)

        return vehicle

    async def _on_task_received(self, msg):
        """Handle incoming task from cloud."""
        try:
            task_data = msg.payload
            vehicle_id = task_data.get("vehicle_id")

            if vehicle_id not in self.vehicles:
                print(f"[VEHICLE-MQTT] Unknown vehicle: {vehicle_id}")
                return

            print(f"[VEHICLE-MQTT] Task received on {vehicle_id}: {task_data.get('task_id')}")

            vehicle_info = self.vehicles[vehicle_id]
            vehicle = vehicle_info["vehicle"]

            # Vehicle receives task
            vehicle.receive_task(task_data)
            vehicle_info["tasks_received"] += 1

            # Publish acknowledgement
            ack = VehicleTaskAck(
                vehicle_id=vehicle_id,
                task_id=task_data.get("task_id"),
                status="received",
                timestamp_s=asyncio.get_event_loop().time()
            )

            msg_id = self.mqtt_bridge.publish_event("VehicleTaskAck", ack.__dict__)
            print(f"[VEHICLE-MQTT] Task ACK published: {msg_id}")

        except Exception as e:
            print(f"[VEHICLE-MQTT] Task receive error: {e}")

    async def _on_handoff(self, msg):
        """Handle handoff event (vehicle moving cells)."""
        try:
            handoff_data = msg.payload
            vehicle_id = handoff_data.get("vehicle_id")

            print(f"[VEHICLE-MQTT] Handoff event for {vehicle_id}")

            if vehicle_id in self.vehicles:
                vehicle = self.vehicles[vehicle_id]["vehicle"]
                vehicle.handle_handoff(handoff_data)

        except Exception as e:
            print(f"[VEHICLE-MQTT] Handoff error: {e}")

    async def _publish_vehicle_online(self, vehicle_id: str):
        """Publish vehicle online signal."""
        event = {
            "vehicle_id": vehicle_id,
            "status": "online",
            "location": self.vehicles[vehicle_id]["vehicle"].location,
        }

        msg_id = self.mqtt_bridge.publish_event("VehicleOnline", event, target_service="fog-service")
        print(f"[VEHICLE-MQTT] Vehicle online published: {msg_id}")

    async def process_tasks(self):
        """Main task processing loop."""
        print("[VEHICLE-MQTT] Starting task processing...")

        while True:
            try:
                # Process each vehicle
                for vehicle_id, info in self.vehicles.items():
                    vehicle = info["vehicle"]
                    agent = info["agent"]

                    # Check if vehicle has pending tasks
                    if vehicle.has_pending_tasks():
                        # Get next task
                        task = vehicle.get_next_task()

                        # Use Agent1 to decide where to execute (fog vs cloud)
                        decision = agent.decide_offload_location(task)

                        print(f"[VEHICLE-MQTT] {vehicle_id} decision: {decision}")

                        # For now, process locally first
                        result = await vehicle.process_task(task)

                        if result:
                            # Publish completion
                            completion = TaskCompleted(
                                vehicle_id=vehicle_id,
                                task_id=task.get("task_id"),
                                result=result,
                                location_decision=decision,
                                timestamp_s=asyncio.get_event_loop().time()
                            )

                            msg_id = self.mqtt_bridge.publish_event(
                                "TaskCompleted",
                                completion.__dict__,
                                target_service="cloud-service",
                                qos=MQTTQoS.AT_LEAST_ONCE
                            )

                            info["tasks_completed"] += 1
                            print(f"[VEHICLE-MQTT] Task completed: {msg_id}")

                await asyncio.sleep(1)

            except Exception as e:
                print(f"[VEHICLE-MQTT] Processing error: {e}")
                await asyncio.sleep(1)

    async def run(self):
        """Run the vehicle service."""
        if not await self.setup():
            print("[VEHICLE-MQTT] Setup failed")
            return

        # Create a few vehicles
        for i in range(3):
            vehicle_id = f"vehicle-{i:03d}"
            await self.create_vehicle(vehicle_id)

        # Run task processing
        await self.process_tasks()

    def stop(self):
        """Stop the service."""
        print("[VEHICLE-MQTT] Stopping...")
        if self.mqtt_bus:
            self.mqtt_bus.disconnect()
        print("[VEHICLE-MQTT] Stopped")


async def main():
    """Entry point."""
    service = VehicleServiceMQTT()

    try:
        await service.run()
    except KeyboardInterrupt:
        print("\n[VEHICLE-MQTT] Interrupted")
        service.stop()


if __name__ == "__main__":
    asyncio.run(main())
