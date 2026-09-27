"""
MQTT-based Distributed Messaging with mTLS and QoS.
Replaces NATS with MQTT for lightweight IoT-focused transport.

Install: pip install paho-mqtt
"""

import asyncio
import json
import uuid
import time
import ssl
from typing import Dict, Any, Callable, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

import paho.mqtt.client as mqtt


class MQTTQoS(Enum):
    """MQTT Quality of Service levels."""
    AT_MOST_ONCE = 0      # Fire and forget
    AT_LEAST_ONCE = 1     # Broker acknowledgement
    EXACTLY_ONCE = 2      # Full handshake


@dataclass
class MQTTMessage:
    """Message wrapper for MQTT transport."""
    id: str
    topic: str
    source_service: str
    target_service: Optional[str]
    payload: Dict[str, Any]
    timestamp_s: float
    qos: int = 1
    retain: bool = False

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(data: str) -> "MQTTMessage":
        d = json.loads(data)
        return MQTTMessage(**d)


class MQTTServiceBus:
    """
    MQTT client with mTLS, QoS, and contract support.
    Connections via paho-mqtt to MQTT broker (mosquitto, EMQX, etc.).
    """

    def __init__(
        self,
        service_name: str,
        broker_host: str = "localhost",
        broker_port: int = 8883,  # Default MQTT with TLS
        cert_dir: str = "certs",
        enable_tls: bool = True,
        qos: MQTTQoS = MQTTQoS.AT_LEAST_ONCE
    ):
        self.service_name = service_name
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.cert_dir = cert_dir
        self.enable_tls = enable_tls
        self.qos = qos.value

        self.client = mqtt.Client(
            client_id=f"{service_name}-{uuid.uuid4().hex[:8]}",
            clean_session=False,
            userdata=self
        )

        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
        self.client.on_subscribe = self._on_subscribe

        # State
        self.connected = False
        self._seen_ids: Dict[str, bool] = {}
        self._dedup_dropped = 0
        self._published = 0
        self._subscribed_handlers: Dict[str, Callable] = {}

        # TLS setup
        if self.enable_tls:
            self._setup_tls()

    def _setup_tls(self):
        """Configure mTLS for MQTT connection."""
        try:
            cert_path = Path(self.cert_dir) / f"{self.service_name}.crt"
            key_path = Path(self.cert_dir) / f"{self.service_name}.key"
            ca_path = Path(self.cert_dir) / "ca.crt"

            if not all([cert_path.exists(), key_path.exists(), ca_path.exists()]):
                print(f"[MQTT] TLS files not found, falling back to no-TLS")
                self.enable_tls = False
                return

            self.client.tls_set(
                ca_certs=str(ca_path),
                certfile=str(cert_path),
                keyfile=str(key_path),
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLSv1_2,
                ciphers=None
            )

            self.client.tls_insecure_set(False)  # Verify broker cert
            print(f"[MQTT] mTLS configured for {self.service_name}")

        except Exception as e:
            print(f"[MQTT] TLS setup error: {e}")
            self.enable_tls = False

    def connect(self) -> bool:
        """Connect to MQTT broker."""
        try:
            print(f"[MQTT] Connecting {self.service_name} to {self.broker_host}:{self.broker_port}...")
            self.client.connect(
                self.broker_host,
                self.broker_port,
                keepalive=60
            )
            self.client.loop_start()  # Background thread
            time.sleep(1)  # Wait for connection
            return self.connected
        except Exception as e:
            print(f"[MQTT] Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from MQTT broker."""
        self.client.loop_stop()
        self.client.disconnect()
        print(f"[MQTT] {self.service_name} disconnected")

    def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        target_service: Optional[str] = None,
        qos: Optional[int] = None
    ) -> str:
        """Publish message with optional dedup."""
        if not self.connected:
            raise RuntimeError("Not connected to MQTT broker")

        msg_id = str(uuid.uuid4())

        # Dedup check
        if msg_id in self._seen_ids:
            self._dedup_dropped += 1
            return msg_id

        # Build MQTT message
        mqtt_msg = MQTTMessage(
            id=msg_id,
            topic=topic,
            source_service=self.service_name,
            target_service=target_service,
            payload=payload,
            timestamp_s=time.time(),
            qos=qos or self.qos
        )

        # Full topic includes target if specified
        full_topic = f"telemetry/{topic}"
        if target_service:
            full_topic = f"telemetry/{topic}/{target_service}"

        # Publish
        self.client.publish(
            full_topic,
            mqtt_msg.to_json(),
            qos=qos or self.qos,
            retain=False
        )

        self._seen_ids[msg_id] = True
        self._published += 1

        print(f"[MQTT] {self.service_name} published {msg_id} → {full_topic}")
        return msg_id

    def subscribe(
        self,
        topic: str,
        handler: Callable,
        qos: Optional[int] = None
    ):
        """Subscribe to topic with handler callback."""
        if not self.connected:
            raise RuntimeError("Not connected to MQTT broker")

        full_topic = f"telemetry/{topic}"

        # Register handler
        self._subscribed_handlers[full_topic] = handler

        # Subscribe
        self.client.subscribe(full_topic, qos=qos or self.qos)
        print(f"[MQTT] {self.service_name} subscribed to {full_topic}")

    def publish_retain(self, topic: str, payload: Dict[str, Any]):
        """Publish with RETAIN flag (broker keeps it for new subscribers)."""
        mqtt_msg = MQTTMessage(
            id=str(uuid.uuid4()),
            topic=topic,
            source_service=self.service_name,
            target_service=None,
            payload=payload,
            timestamp_s=time.time()
        )

        full_topic = f"telemetry/{topic}"
        self.client.publish(
            full_topic,
            mqtt_msg.to_json(),
            qos=1,
            retain=True  # Retain on broker
        )

    def request_reply(
        self,
        topic: str,
        payload: Dict[str, Any],
        target_service: Optional[str] = None,
        timeout_s: float = 5.0
    ) -> Optional[Dict[str, Any]]:
        """
        Request-reply pattern.
        Note: MQTT doesn't natively support request-reply, so this uses a temporary topic.
        """
        request_id = str(uuid.uuid4())
        reply_topic = f"reply/{request_id}"
        response_store = {}

        def reply_handler(client, userdata, msg):
            try:
                mqtt_msg = MQTTMessage.from_json(msg.payload.decode())
                response_store['data'] = mqtt_msg.payload
            except Exception as e:
                print(f"[MQTT] Reply handler error: {e}")

        # Subscribe to reply topic
        self.client.subscribe(reply_topic, qos=1)
        self.client.message_callback_add(reply_topic, reply_handler)

        # Publish request
        full_topic = f"request/{topic}"
        if target_service:
            full_topic = f"request/{topic}/{target_service}"

        request_msg = MQTTMessage(
            id=request_id,
            topic=topic,
            source_service=self.service_name,
            target_service=target_service,
            payload={"request_id": request_id, "reply_topic": reply_topic, **payload},
            timestamp_s=time.time()
        )

        self.client.publish(full_topic, request_msg.to_json(), qos=1)

        # Wait for reply with timeout
        start = time.time()
        while time.time() - start < timeout_s:
            if 'data' in response_store:
                return response_store['data']
            time.sleep(0.1)

        print(f"[MQTT] Request {request_id} timed out")
        return None

    def _on_connect(self, client, userdata, flags, rc):
        """Called when client connects to broker."""
        if rc == 0:
            self.connected = True
            print(f"[MQTT] {self.service_name} connected successfully")
            # Re-subscribe to all topics
            for topic in self._subscribed_handlers.keys():
                client.subscribe(topic, qos=self.qos)
        else:
            print(f"[MQTT] Connection failed with code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Called when client disconnects."""
        self.connected = False
        if rc != 0:
            print(f"[MQTT] Unexpected disconnection: {rc}")

    def _on_message(self, client, userdata, msg):
        """Called when message is received."""
        try:
            mqtt_msg = MQTTMessage.from_json(msg.payload.decode())

            # Dedup
            if mqtt_msg.id in self._seen_ids:
                return

            self._seen_ids[mqtt_msg.id] = True

            # Call handler
            handler = self._subscribed_handlers.get(msg.topic)
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(mqtt_msg))
                else:
                    handler(mqtt_msg)

        except Exception as e:
            print(f"[MQTT] Message error: {e}")

    def _on_publish(self, client, userdata, mid):
        """Called when publish completes."""
        pass

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Called when subscribe completes."""
        print(f"[MQTT] Subscribe acknowledged (QoS: {granted_qos})")

    def status(self) -> Dict[str, Any]:
        """Get bus status."""
        return {
            "service": self.service_name,
            "connected": self.connected,
            "broker": f"{self.broker_host}:{self.broker_port}",
            "published": self._published,
            "dedupDropped": self._dedup_dropped,
            "subscriptions": list(self._subscribed_handlers.keys()),
            "mtlsEnabled": self.enable_tls,
            "qos": self.qos,
        }


class MQTTEventBridge:
    """Bridge between contract events and MQTT topics."""

    def __init__(self, bus: MQTTServiceBus):
        self.bus = bus
        self.topic_map = {
            "VehicleTaskSubmitted": "vehicle/task-submitted",
            "FogDecisionMade": "fog/decision",
            "HandoffTriggered": "mobility/handoff",
            "CloudForwarded": "cloud/forwarded",
            "TaskCompleted": "task/completed",
        }

    def publish_event(
        self,
        event_type: str,
        event_payload: Dict[str, Any],
        target_service: Optional[str] = None,
        qos: MQTTQoS = MQTTQoS.AT_LEAST_ONCE
    ) -> str:
        """Publish a contract event."""
        topic = self.topic_map.get(event_type, f"custom/{event_type}")
        return self.bus.publish(topic, event_payload, target_service=target_service, qos=qos.value)

    def subscribe_events(self, handler: Callable, qos: MQTTQoS = MQTTQoS.AT_LEAST_ONCE):
        """Subscribe to all telemetry events."""
        for topic in self.topic_map.values():
            self.bus.subscribe(topic, handler, qos=qos.value)


def mqtt_broker_docker_command() -> str:
    """Return Docker command to start MQTT broker (mosquitto)."""
    return """
# Start MQTT broker with TLS support
docker run -d \\
  --name mosquitto \\
  -p 1883:1883 \\
  -p 8883:8883 \\
  -v $(pwd)/mosquitto.conf:/mosquitto/config/mosquitto.conf \\
  -v $(pwd)/certs:/mosquitto/certs \\
  eclipse-mosquitto:latest
"""


def mqtt_broker_config() -> str:
    """MQTT broker configuration (mosquitto.conf)."""
    return """
# Mosquitto MQTT Broker Configuration

# Ports
listener 1883
protocol mqtt

listener 8883
protocol mqtt
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/mosquitto.crt
keyfile /mosquitto/certs/mosquitto.key
require_certificate true

# Persistence
persistence true
persistence_location /mosquitto/data/

# Authentication (optional, can add)
# allow_anonymous false
# password_file /mosquitto/config/passwd

# Logging
log_dest stdout
log_dest file /mosquitto/log/mosquitto.log
log_type all
"""
