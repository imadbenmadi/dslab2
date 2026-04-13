"""
MQTT-enabled Cloud Service.
Provides API, analytics, and model management with MQTT messaging.

Run: python -m services.cloud_service_mqtt
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from collections import defaultdict

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, jsonify, request
from flask_cors import CORS
import threading

from infrastructure.mqtt_bus import MQTTServiceBus, MQTTEventBridge, MQTTQoS
from infrastructure.model_signing import ModelArtifactManager
from infrastructure.pki_manager import PKIManager
from infrastructure.openflow_controller import bootstrap_openflow_controller


class CloudServiceMQTT:
    """Cloud service with MQTT messaging and analytics."""

    def __init__(
        self,
        mqtt_host: str = None,
        mqtt_port: int = None,
        cert_dir: str = "certs",
        api_port: int = 5000
    ):
        self.mqtt_host = mqtt_host or os.getenv("MQTT_HOST", "localhost")
        self.mqtt_port = mqtt_port or int(os.getenv("MQTT_PORT", 8883))
        self.cert_dir = cert_dir
        self.api_port = api_port

        self.mqtt_bus = None
        self.mqtt_bridge = None
        self.pki_manager = None
        self.model_manager = None
        self.openflow_controller = None

        # Analytics storage
        self.metrics = defaultdict(int)
        self.task_history = []
        self.vehicle_status = {}

        # Flask app
        self.app = Flask(__name__)
        CORS(self.app)
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask API routes."""

        @self.app.route("/health", methods=["GET"])
        def health():
            return jsonify({
                "status": "ok",
                "mqtt_connected": self.mqtt_bus.connected if self.mqtt_bus else False,
                "metrics": dict(self.metrics),
            })

        @self.app.route("/metrics", methods=["GET"])
        def metrics():
            return jsonify({
                "tasks_total": self.metrics["tasks_total"],
                "tasks_completed": self.metrics["tasks_completed"],
                "tasks_failed": self.metrics["tasks_failed"],
                "vehicles_online": len(self.vehicle_status),
            })

        @self.app.route("/vehicles", methods=["GET"])
        def vehicles():
            return jsonify(self.vehicle_status)

        @self.app.route("/tasks", methods=["GET"])
        def tasks():
            limit = request.args.get("limit", 100, type=int)
            return jsonify(self.task_history[-limit:])

        @self.app.route("/models/list", methods=["GET"])
        def list_models():
            models = []
            if self.model_manager:
                models = list(self.model_manager.registry.values())
            return jsonify({"models": models})

        @self.app.route("/models/verify/<model_name>/<model_version>", methods=["GET"])
        def verify_model(model_name, model_version):
            if not self.model_manager:
                return jsonify({"error": "Model manager not initialized"}), 500

            try:
                result = self.model_manager.verify_model(model_name, model_version)
                return jsonify({
                    "model": model_name,
                    "version": model_version,
                    "verified": result,
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @self.app.route("/mqtt/status", methods=["GET"])
        def mqtt_status():
            if not self.mqtt_bus:
                return jsonify({"error": "MQTT not initialized"}), 500

            return jsonify(self.mqtt_bus.status())

        @self.app.route("/openflow/flows", methods=["GET"])
        def of_flows():
            if not self.openflow_controller:
                return jsonify({"error": "OpenFlow not initialized"}), 500

            stats = self.openflow_controller.get_network_statistics()
            return jsonify(stats)

        @self.app.route("/openflow/export", methods=["GET"])
        def of_export():
            if not self.openflow_controller:
                return jsonify({"error": "OpenFlow not initialized"}), 500

            commands = self.openflow_controller.export_flows_to_ovs_commands()
            return jsonify({"ovs_commands": commands})

    async def setup(self) -> bool:
        """Initialize MQTT, PKI, models, and OpenFlow."""
        print(f"[CLOUD-MQTT] Setting up cloud service...")
        print(f"  MQTT broker: {self.mqtt_host}:{self.mqtt_port}")
        print(f"  API port: {self.api_port}")
        print(f"  Cert dir: {self.cert_dir}")

        try:
            # Initialize PKI
            self.pki_manager = PKIManager(
                root_cert_path=f"{self.cert_dir}/root-ca.crt",
                root_key_path=f"{self.cert_dir}/root-ca.key"
            )

            # Create MQTT bus
            self.mqtt_bus = MQTTServiceBus(
                service_name="cloud-service",
                broker_host=self.mqtt_host,
                broker_port=self.mqtt_port,
                cert_dir=self.cert_dir,
                enable_tls=True,
                qos=MQTTQoS.AT_LEAST_ONCE
            )

            # Create event bridge
            self.mqtt_bridge = MQTTEventBridge(self.mqtt_bus)

            # Initialize model signing
            try:
                key_path = Path(self.cert_dir) / "cloud-service.key"
                cert_path = Path(self.cert_dir) / "cloud-service.crt"

                self.model_manager = ModelArtifactManager(
                    signer_key_path=str(key_path),
                    signer_cert_path=str(cert_path)
                )
                print("[CLOUD-MQTT] Model signing initialized")
            except Exception as e:
                print(f"[CLOUD-MQTT] Model signing not available: {e}")

            # Initialize OpenFlow controller
            try:
                self.openflow_controller = bootstrap_openflow_controller()
                print("[CLOUD-MQTT] OpenFlow controller initialized")
            except Exception as e:
                print(f"[CLOUD-MQTT] OpenFlow not available: {e}")

            # Connect to MQTT
            if not self.mqtt_bus.connect():
                print("[CLOUD-MQTT] Failed to connect to MQTT broker")
                return False

            # Subscribe to task completion events
            self.mqtt_bus.subscribe(
                "task/completed",
                self._on_task_completed,
                qos=MQTTQoS.AT_LEAST_ONCE.value
            )

            # Subscribe to fog decisions
            self.mqtt_bus.subscribe(
                "fog/decision",
                self._on_fog_decision,
                qos=MQTTQoS.AT_LEAST_ONCE.value
            )

            print("[CLOUD-MQTT] Setup complete")
            return True

        except Exception as e:
            print(f"[CLOUD-MQTT] Setup error: {e}")
            return False

    async def _on_task_completed(self, msg):
        """Handle task completion from vehicles/fog."""
        try:
            task_data = msg.payload
            vehicle_id = task_data.get("vehicle_id")
            task_id = task_data.get("task_id")

            print(f"[CLOUD-MQTT] Task completed: {task_id} from {vehicle_id}")

            # Update analytics
            self.metrics["tasks_completed"] += 1
            self.task_history.append({
                "task_id": task_id,
                "vehicle_id": vehicle_id,
                "status": "completed",
                "timestamp": msg.timestamp_s,
            })

            # Update vehicle status
            self.vehicle_status[vehicle_id] = {
                "status": "idle",
                "last_task": task_id,
            }

        except Exception as e:
            print(f"[CLOUD-MQTT] Task completion error: {e}")

    async def _on_fog_decision(self, msg):
        """Handle fog routing decision."""
        try:
            decision_data = msg.payload
            fog_id = decision_data.get("fog_id")
            vehicle_id = decision_data.get("vehicle_id")
            decision = decision_data.get("routing_decision")

            print(f"[CLOUD-MQTT] Fog decision: {fog_id} → {decision} for {vehicle_id}")

            # If routing to cloud, generate a task
            if decision == "cloud":
                task_id = f"cloud-task-{self.metrics['tasks_total']:06d}"
                self.metrics["tasks_total"] += 1

                task_event = {
                    "task_id": task_id,
                    "vehicle_id": vehicle_id,
                    "fog_id": fog_id,
                    "location": "cloud",
                }

                # Can forward to agents or store for processing
                self.task_history.append(task_event)

        except Exception as e:
            print(f"[CLOUD-MQTT] Fog decision error: {e}")

    async def submit_task(self, vehicle_id: str, task_definition: dict) -> str:
        """Programmatically submit a task to a vehicle."""
        task_id = f"task-{self.metrics['tasks_total']:06d}"
        self.metrics["tasks_total"] += 1

        task = {
            "task_id": task_id,
            "vehicle_id": vehicle_id,
            "definition": task_definition,
        }

        # Publish to vehicle
        msg_id = self.mqtt_bridge.publish_event(
            "VehicleTaskSubmitted",
            task,
            target_service="vehicle-service",
            qos=MQTTQoS.AT_LEAST_ONCE
        )

        self.task_history.append(task)
        return task_id

    def run_api(self):
        """Run Flask API server."""
        print(f"[CLOUD-MQTT] Starting Flask API on 0.0.0.0:{self.api_port}")
        self.app.run(host="0.0.0.0", port=self.api_port, debug=False, threaded=True)

    async def run(self):
        """Run the cloud service."""
        if not await self.setup():
            print("[CLOUD-MQTT] Setup failed")
            return

        # Start Flask API in background thread
        api_thread = threading.Thread(target=self.run_api, daemon=True)
        api_thread.start()

        # Run main event loop
        while True:
            try:
                await asyncio.sleep(1)
            except KeyboardInterrupt:
                break

    def stop(self):
        """Stop the service."""
        print("[CLOUD-MQTT] Stopping...")
        if self.mqtt_bus:
            self.mqtt_bus.disconnect()
        print("[CLOUD-MQTT] Stopped")


async def main():
    """Entry point."""
    service = CloudServiceMQTT()

    try:
        await service.run()
    except KeyboardInterrupt:
        print("\n[CLOUD-MQTT] Interrupted")
        service.stop()


if __name__ == "__main__":
    asyncio.run(main())
