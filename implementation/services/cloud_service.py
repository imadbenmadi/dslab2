"""
Cloud Service - Runs Flask API, WebSocket, analytics, control plane.
Connects fog and vehicle services via NATS with mTLS.

Run: python -m services.cloud_service
"""

import asyncio
import threading
import time
import json
from typing import Dict, Optional
from dataclasses import dataclass

from flask import Flask
from flask_cors import CORS
from infrastructure.nats_bus import NatsServiceBus, NatsEventBridge, NatsMessage
from infrastructure.cert_manager import get_mtls_config
from visualization.websocket_server import WebSocketServer
from visualization.api_server import app as api_app


@dataclass
class AnalyticsMetrics:
    tasks_submitted: int = 0
    tasks_completed: int = 0
    tasks_offloaded_to_fog: int = 0
    tasks_offloaded_to_cloud: int = 0
    total_latency_ms: float = 0.0


class CloudService:
    """Cloud-side service: API, WebSocket, analytics, control plane."""

    def __init__(self, nats_url: str = "nats://localhost:4222", cert_dir: str = "certs"):
        self.nats_url = nats_url
        self.cert_dir = cert_dir

        # NATS messaging
        self.nats_bus = NatsServiceBus(
            service_name="cloud-service",
            nats_url=nats_url,
            cert_dir=cert_dir,
            enable_tls=True
        )
        self.event_bridge = NatsEventBridge(self.nats_bus)

        # WebSocket server for live updates
        self.ws_server = WebSocketServer(host="127.0.0.1", port=8765)

        # Analytics
        self.metrics = AnalyticsMetrics()
        self.task_log: Dict[str, dict] = {}

        # Flask app
        self.flask_app = api_app
        CORS(self.flask_app)

        # Add cloud-specific endpoints
        self._setup_cloud_endpoints()

        # Event handlers registered
        self.running = False

    def _setup_cloud_endpoints(self):
        """Register cloud-service specific API endpoints."""

        @self.flask_app.route("/api/cloud/analytics", methods=["GET"])
        def get_analytics():
            return {
                "tasksSubmitted": self.metrics.tasks_submitted,
                "tasksCompleted": self.metrics.tasks_completed,
                "tasksOffloadedToFog": self.metrics.tasks_offloaded_to_fog,
                "tasksOffloadedToCloud": self.metrics.tasks_offloaded_to_cloud,
                "avgLatencyMs": (
                    self.metrics.total_latency_ms / max(1, self.metrics.tasks_completed)
                    if self.metrics.tasks_completed > 0
                    else 0.0
                ),
                "taskLog": {k: v for k, v in list(self.task_log.items())[-100:]},
            }

        @self.flask_app.route("/api/cloud/status", methods=["GET"])
        def get_cloud_status():
            return {
                "service": "cloud-service",
                "nats_connected": self.nats_bus.conn is not None,
                "websocket_clients": len(self.ws_server.clients) if self.ws_server else 0,
                "metrics": {
                    "tasksSubmitted": self.metrics.tasks_submitted,
                    "tasksCompleted": self.metrics.tasks_completed,
                },
            }

    async def _handle_telemetry_events(self, msg: NatsMessage):
        """Handle incoming telemetry events from fog/vehicle services."""
        topic = msg.topic
        payload = msg.payload

        if "task-submitted" in topic:
            self.metrics.tasks_submitted += 1
            print(f"[C-SVC] Task submitted: {payload.get('task_id')}")

        elif "decision" in topic:
            decision = payload.get("decision")
            if decision == "fog":
                self.metrics.tasks_offloaded_to_fog += 1
            elif decision == "cloud":
                self.metrics.tasks_offloaded_to_cloud += 1
            print(f"[C-SVC] Decision made: {decision}")

        elif "completed" in topic:
            self.metrics.tasks_completed += 1
            self.metrics.total_latency_ms += payload.get("latency_ms", 0)
            print(f"[C-SVC] Task completed: {payload.get('task_id')}")

        # Log and broadcast to WebSocket
        task_id = payload.get("task_id", "unknown")
        self.task_log[task_id] = {
            "topic": topic,
            "payload": payload,
            "timestamp": time.time(),
        }

        # Broadcast metrics update to UI (via WebSocket)
        if self.ws_server:
            try:
                await self.ws_server.broadcast_metrics({
                    "metrics": {
                        "tasksSubmitted": self.metrics.tasks_submitted,
                        "tasksCompleted": self.metrics.tasks_completed,
                    },
                    "latestEvent": topic,
                })
            except Exception as e:
                print(f"[C-SVC] WebSocket broadcast error: {e}")

    async def _run_nats_listener(self):
        """Listen to all telemetry events from NATS."""
        await self.event_bridge.subscribe_events(self._handle_telemetry_events)

    async def _run_flask_server(self):
        """Run Flask app in separate thread."""
        def run_flask():
            self.flask_app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

        thread = threading.Thread(target=run_flask, daemon=True)
        thread.start()
        print("[C-SVC] Flask API started on http://127.0.0.1:5000")

    async def _run_websocket_server(self):
        """Run WebSocket server in separate thread."""
        def run_ws():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                loop.run_until_complete(self.ws_server.start_server())
            except Exception as e:
                print(f"[C-SVC] WebSocket error: {e}")

        thread = threading.Thread(target=run_ws, daemon=True)
        thread.start()
        print("[C-SVC] WebSocket server started on ws://127.0.0.1:8765")

    async def start(self):
        """Start the cloud service."""
        print("[C-SVC] Starting cloud service...")
        await self.nats_bus.connect()

        self.running = True

        # Start Flask and WebSocket in parallel threads
        await self._run_flask_server()
        await self._run_websocket_server()

        # Listen to NATS events
        await self._run_nats_listener()

    async def stop(self):
        """Stop the service gracefully."""
        print("[C-SVC] Stopping...")
        self.running = False
        await self.nats_bus.disconnect()


async def main():
    service = CloudService()
    try:
        await service.start()
    except KeyboardInterrupt:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
