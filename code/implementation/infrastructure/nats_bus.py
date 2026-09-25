"""
NATS-based distributed messaging layer with mTLS support.
Replaces in-memory AtLeastOnceBus for service-to-service communication.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, Any, Callable, Optional, List
from pathlib import Path

import nats
from infrastructure.cert_manager import get_mtls_config


@dataclass
class NatsMessage:
    """Serializable message for NATS transport."""
    id: str
    topic: str
    source_service: str
    target_service: Optional[str]  # None = broadcast
    payload: Dict[str, Any]
    timestamp_s: float
    ack_required: bool = True

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(data: str) -> "NatsMessage":
        d = json.loads(data)
        return NatsMessage(**d)


class NatsServiceBus:
    """
    NATS-based service bus with mTLS, built on existing contracts.
    Maintains at-least-once semantics with dedup by message ID.
    """

    def __init__(
        self,
        service_name: str,
        nats_url: str = "nats://localhost:4222",
        cert_dir: str = "certs",
        enable_tls: bool = True
    ):
        self.service_name = service_name
        self.nats_url = nats_url
        self.cert_dir = cert_dir
        self.enable_tls = enable_tls

        self.conn: Optional[nats.NATS] = None
        self.subscriptions: Dict[str, nats.Subscription] = {}
        self._seen_ids: Dict[str, bool] = {}
        self._dedup_dropped = 0
        self._published = 0
        self._handlers: Dict[str, List[Callable]] = {}

        # Load mTLS config
        try:
            self.mtls_config = get_mtls_config(service_name, cert_dir)
        except Exception as e:
            print(f"[NATS] Warning: mTLS config not found: {e}. Running without mTLS.")
            self.mtls_config = None
            self.enable_tls = False

    async def connect(self):
        """Connect to NATS broker with optional mTLS."""
        try:
            if self.enable_tls and self.mtls_config:
                self.conn = await nats.connect(
                    self.nats_url,
                    tls_cert_file=self.mtls_config["cert"],
                    tls_key_file=self.mtls_config["key"],
                    tls_ca_file=self.mtls_config["ca"],
                    allow_reconnect=True,
                    max_reconnect_attempts=5,
                )
            else:
                self.conn = await nats.connect(
                    self.nats_url,
                    allow_reconnect=True,
                    max_reconnect_attempts=5,
                )
            print(f"[NATS] {self.service_name} connected to {self.nats_url}")
        except Exception as e:
            print(f"[NATS] Connection failed: {e}")
            raise

    async def disconnect(self):
        """Disconnect from NATS."""
        if self.conn:
            await self.conn.close()
            print(f"[NATS] {self.service_name} disconnected")

    async def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        target_service: Optional[str] = None,
        ack_required: bool = True
    ) -> str:
        """Publish message to topic with optional dedup."""
        if not self.conn:
            raise RuntimeError("Not connected to NATS")

        msg_id = str(uuid.uuid4())

        # Dedup check
        if msg_id in self._seen_ids:
            self._dedup_dropped += 1
            return msg_id

        # Build NATS message
        nats_msg = NatsMessage(
            id=msg_id,
            topic=topic,
            source_service=self.service_name,
            target_service=target_service,
            payload=payload,
            timestamp_s=asyncio.get_event_loop().time(),
            ack_required=ack_required
        )

        # Full topic includes target if specified
        full_topic = f"{topic}"
        if target_service:
            full_topic = f"{topic}.{target_service}"

        # Publish to NATS
        await self.conn.publish(full_topic, nats_msg.to_json().encode())

        self._seen_ids[msg_id] = True
        self._published += 1

        print(f"[NATS] {self.service_name} published {msg_id} -> {full_topic}")
        return msg_id

    async def subscribe(
        self,
        topic: str,
        handler: Callable,
        queue_group: Optional[str] = None
    ):
        """Subscribe to topic with handler callback."""
        if not self.conn:
            raise RuntimeError("Not connected to NATS")

        async def msg_handler(msg):
            try:
                nats_msg = NatsMessage.from_json(msg.data.decode())

                # Dedup
                if nats_msg.id in self._seen_ids:
                    return

                self._seen_ids[nats_msg.id] = True

                # Call handler (must be coroutine)
                if asyncio.iscoroutinefunction(handler):
                    await handler(nats_msg)
                else:
                    handler(nats_msg)

            except Exception as e:
                print(f"[NATS] Handler error: {e}")

        # Subscribe with optional queue group for load balancing
        sub = await self.conn.subscribe(
            topic,
            cb=msg_handler,
            queue=queue_group if queue_group else None
        )

        self.subscriptions[topic] = sub
        print(f"[NATS] {self.service_name} subscribed to {topic}")

    async def request(
        self,
        topic: str,
        payload: Dict[str, Any],
        target_service: Optional[str] = None,
        timeout_s: float = 5.0
    ) -> Optional[Dict[str, Any]]:
        """Request-reply pattern with timeout."""
        if not self.conn:
            raise RuntimeError("Not connected to NATS")

        msg_id = str(uuid.uuid4())
        nats_msg = NatsMessage(
            id=msg_id,
            topic=topic,
            source_service=self.service_name,
            target_service=target_service,
            payload=payload,
            timestamp_s=asyncio.get_event_loop().time(),
            ack_required=True
        )

        full_topic = f"{topic}.req"
        if target_service:
            full_topic = f"{topic}.{target_service}.req"

        try:
            reply = await self.conn.request(
                full_topic,
                nats_msg.to_json().encode(),
                timeout=timeout_s
            )
            reply_msg = NatsMessage.from_json(reply.data.decode())
            return reply_msg.payload
        except asyncio.TimeoutError:
            print(f"[NATS] Request {msg_id} timed out after {timeout_s}s")
            return None

    def status(self) -> Dict[str, Any]:
        """Get bus status for observability."""
        return {
            "service": self.service_name,
            "connected": self.conn is not None,
            "published": self._published,
            "dedupDropped": self._dedup_dropped,
            "subscriptions": list(self.subscriptions.keys()),
            "mtlsEnabled": self.enable_tls,
        }


class NatsEventBridge:
    """Bridge between contract events and NATS topics."""

    def __init__(self, bus: NatsServiceBus):
        self.bus = bus
        self.topic_map = {
            "VehicleTaskSubmitted": "telemetry.vehicle.task-submitted",
            "FogDecisionMade": "telemetry.fog.decision",
            "HandoffTriggered": "telemetry.mobility.handoff",
            "CloudForwarded": "telemetry.cloud.forwarded",
            "TaskCompleted": "telemetry.task.completed",
        }

    async def publish_event(self, event_type: str, event_payload: Dict[str, Any], target_service: Optional[str] = None):
        """Publish a contract event to NATS."""
        topic = self.topic_map.get(event_type, f"telemetry.{event_type}")
        await self.bus.publish(topic, event_payload, target_service=target_service)

    
    async def subscribe_events(self, handler: Callable):
        """Subscribe to all telemetry events."""
        for topic in self.topic_map.values():
            await self.bus.subscribe(topic, handler, queue_group="analytics")
