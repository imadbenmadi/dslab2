"""
MQTT + PKI Integration Layer.
Manages certificate provisioning and renewal for MQTT services with mTLS.
"""

import os
from pathlib import Path
from typing import Tuple, Optional
import threading
import time

from infrastructure.pki_manager import PKIManager
from infrastructure.mqtt_bus import MQTTServiceBus


class MQTTServiceProvisioner:
    """
    Provisions MQTT services with PKI-managed certificates.
    Handles cert generation, rotation, and lifecycle.
    """

    def __init__(
        self,
        pki_manager: PKIManager,
        cert_dir: str = "certs",
        broker_host: str = "localhost",
        broker_port: int = 8883
    ):
        self.pki = pki_manager
        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(exist_ok=True)

        self.broker_host = broker_host
        self.broker_port = broker_port

        # Track provisioned services
        self.services: dict = {}
        self._rotation_threads: dict = {}

    def provision_service(
        self,
        service_name: str,
        service_role: str = None
    ) -> Tuple[str, str, str]:
        """
        Generate or retrieve MQTT service certificates.
        Returns: (cert_path, key_path, ca_path)
        """
        if service_role is None:
            service_role = service_name

        cert_path = self.cert_dir / f"{service_name}.crt"
        key_path = self.cert_dir / f"{service_name}.key"
        ca_path = self.cert_dir / "ca.crt"

        # If already provisioned and valid, return
        if cert_path.exists() and key_path.exists():
            if self.pki.is_certificate_valid(str(cert_path)):
                print(f"[MQTT-PKI] {service_name} cert already provisioned and valid")
                self.services[service_name] = {
                    "cert_path": str(cert_path),
                    "key_path": str(key_path),
                    "ca_path": str(ca_path),
                    "role": service_role
                }
                return str(cert_path), str(key_path), str(ca_path)

        # Generate new certificate
        print(f"[MQTT-PKI] Generating certificate for {service_name}...")
        cert_data, key_data, chain_data = self.pki.generate_service_certificate(
            service_name,
            service_role
        )

        # Write to files
        cert_path.write_text(cert_data)
        key_path.write_text(key_data)
        ca_path.write_text(chain_data)

        print(f"[MQTT-PKI] Provisioned {service_name}:")
        print(f"  - Cert: {cert_path}")
        print(f"  - Key: {key_path}")
        print(f"  - CA: {ca_path}")

        self.services[service_name] = {
            "cert_path": str(cert_path),
            "key_path": str(key_path),
            "ca_path": str(ca_path),
            "role": service_role
        }

        return str(cert_path), str(key_path), str(ca_path)

    def create_mqtt_bus(self, service_name: str) -> MQTTServiceBus:
        """
        Create MQTT service bus with provisioned certificates.
        """
        cert_path, key_path, ca_path = self.provision_service(service_name)

        bus = MQTTServiceBus(
            service_name=service_name,
            broker_host=self.broker_host,
            broker_port=self.broker_port,
            cert_dir=str(self.cert_dir),
            enable_tls=True
        )

        return bus

    def start_rotation_watcher(
        self,
        service_name: str,
        check_interval_s: int = 86400  # 24 hours
    ):
        """
        Start background thread to watch and rotate service certificates.
        """
        if service_name in self._rotation_threads:
            print(f"[MQTT-PKI] Rotation watcher already running for {service_name}")
            return

        def rotation_task():
            while True:
                try:
                    time.sleep(check_interval_s)
                    self._check_and_rotate(service_name)
                except Exception as e:
                    print(f"[MQTT-PKI] Rotation task error for {service_name}: {e}")

        thread = threading.Thread(target=rotation_task, daemon=True, name=f"mqtt-rotation-{service_name}")
        thread.start()
        self._rotation_threads[service_name] = thread
        print(f"[MQTT-PKI] Rotation watcher started for {service_name} (check every {check_interval_s}s)")

    def _check_and_rotate(self, service_name: str):
        """Check certificate rotation needs and auto-rotate."""
        cert_path = self.cert_dir / f"{service_name}.crt"

        if not cert_path.exists():
            return

        rotation_needed = self.pki.check_rotation_needed([str(cert_path)])

        if rotation_needed:
            print(f"[MQTT-PKI] Rotating certificate for {service_name}...")
            old_cert = str(cert_path)
            new_cert, new_key, new_chain = self.pki.rotate_certificate(
                old_cert,
                service_name,
                self.services.get(service_name, {}).get("role", service_name)
            )

            # Update files
            (self.cert_dir / f"{service_name}.crt").write_text(new_cert)
            (self.cert_dir / f"{service_name}.key").write_text(new_key)
            (self.cert_dir / "ca.crt").write_text(new_chain)

            print(f"[MQTT-PKI] Certificate rotated for {service_name}")

    def provision_broker(self) -> Tuple[str, str, str]:
        """Generate broker (mosquitto) certificates."""
        return self.provision_service("mosquitto", "mqtt-broker")

    def get_service_certs(self, service_name: str) -> Optional[dict]:
        """Retrieve cert info for a service."""
        return self.services.get(service_name)

    def list_provisioned_services(self) -> list:
        """List all provisioned MQTT services."""
        return list(self.services.keys())

    def export_cert_bundle(self, output_path: str = "mqtt-certs.tar.gz"):
        """Export all certificates as tarball for deployment."""
        import tarfile

        output = Path(output_path)

        with tarfile.open(output, "w:gz") as tar:
            for item in self.cert_dir.glob("*.crt"):
                tar.add(item, arcname=item.name)
            for item in self.cert_dir.glob("*.key"):
                tar.add(item, arcname=item.name)

        print(f"[MQTT-PKI] Certificate bundle exported to {output_path}")
        return str(output)

    def status(self) -> dict:
        """Get provisioner status."""
        return {
            "services": self.services,
            "rotationWatchers": list(self._rotation_threads.keys()),
            "broker": f"{self.broker_host}:{self.broker_port}",
            "certDir": str(self.cert_dir),
        }


def bootstrap_mqtt_infrastructure(
    cert_dir: str = "certs",
    broker_host: str = "localhost",
    broker_port: int = 8883
) -> Tuple[PKIManager, MQTTServiceProvisioner]:
    """
    Bootstrap full MQTT infrastructure with PKI certificates.

    Returns:
        (pki_manager, mqtt_provisioner)
    """
    print("[MQTT-BOOTSTRAP] Starting MQTT infrastructure...")

    # Initialize PKI
    pki = PKIManager(root_cert_path=f"{cert_dir}/root-ca.crt", root_key_path=f"{cert_dir}/root-ca.key")

    # Initialize provisioner
    provisioner = MQTTServiceProvisioner(
        pki_manager=pki,
        cert_dir=cert_dir,
        broker_host=broker_host,
        broker_port=broker_port
    )

    # Provision broker
    print("[MQTT-BOOTSTRAP] Provisioning MQTT broker (mosquitto)...")
    provisioner.provision_broker()

    # Provision standard services
    services = [
        ("vehicle-service", "vehicle"),
        ("fog-service", "fog"),
        ("cloud-service", "cloud"),
    ]

    for service_name, role in services:
        print(f"[MQTT-BOOTSTRAP] Provisioning {service_name}...")
        provisioner.provision_service(service_name, role)
        # Start rotation watcher
        provisioner.start_rotation_watcher(service_name)

    print("[MQTT-BOOTSTRAP] Infrastructure ready")
    print(f"  - Broker: {broker_host}:{broker_port}")
    print(f"  - Services: {provisioner.list_provisioned_services()}")
    print(f"  - Cert dir: {cert_dir}")

    return pki, provisioner


# Kubernetes-ready configuration
K8S_MQTT_DEPLOYMENT = """
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: mosquitto-config
data:
  mosquitto.conf: |
    listener 1883
    protocol mqtt
    listener 8883
    protocol mqtt
    cafile /etc/mqtt/certs/ca.crt
    certfile /etc/mqtt/certs/mosquitto.crt
    keyfile /etc/mqtt/certs/mosquitto.key
    require_certificate true
    persistence true
    persistence_location /mosquitto/data/

---
apiVersion: v1
kind: Secret
metadata:
  name: mqtt-certs
type: Opaque
stringData:
  ca.crt: |
    -----BEGIN CERTIFICATE-----
    [CA certificate content]
    -----END CERTIFICATE-----
  mosquitto.crt: |
    -----BEGIN CERTIFICATE-----
    [Broker certificate content]
    -----END CERTIFICATE-----
  mosquitto.key: |
    -----BEGIN PRIVATE KEY-----
    [Broker private key content]
    -----END PRIVATE KEY-----

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mosquitto
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mosquitto
  template:
    metadata:
      labels:
        app: mosquitto
    spec:
      containers:
      - name: mosquitto
        image: eclipse-mosquitto:latest
        ports:
        - containerPort: 1883
          name: mqtt
        - containerPort: 8883
          name: mqtt-tls
        volumeMounts:
        - name: config
          mountPath: /mosquitto/config
        - name: certs
          mountPath: /etc/mqtt/certs
        - name: data
          mountPath: /mosquitto/data
      volumes:
      - name: config
        configMap:
          name: mosquitto-config
      - name: certs
        secret:
          secretName: mqtt-certs
      - name: data
        emptyDir: {}

---
apiVersion: v1
kind: Service
metadata:
  name: mosquitto
spec:
  selector:
    app: mosquitto
  ports:
  - port: 1883
    targetPort: 1883
    name: mqtt
  - port: 8883
    targetPort: 8883
    name: mqtt-tls
  type: ClusterIP
"""
