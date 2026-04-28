"""
MQTT-enabled Service Orchestrator with PKI.
Launches all three services with MQTT messaging and mTLS certificates.

Run: python -m services.orchestrator_mqtt
"""

import subprocess
import sys
import time
import os
import socket
from pathlib import Path
from typing import Optional

from infrastructure.pki_manager import PKIManager
from infrastructure.mqtt_pki_integration import bootstrap_mqtt_infrastructure


class MQTTServiceOrchestrator:
    """Orchestrate startup of all three distributed services with MQTT + PKI."""

    def __init__(
        self,
        cert_dir: str = "certs",
        mqtt_host: str = "localhost",
        mqtt_port: int = 8883,
        mqtt_plaintext_port: int = 1883,
        start_broker: bool = False
    ):
        self.cert_dir = cert_dir
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_plaintext_port = mqtt_plaintext_port
        self.start_broker = start_broker
        self.processes = {}
        self.pki_manager: Optional[PKIManager] = None
        self.mqtt_provisioner = None

    def _bootstrap_mqtt_infrastructure(self):
        """Initialize PKI and MQTT certificate provisioning."""
        print("[ORCH-MQTT] Bootstrapping MQTT infrastructure...")
        try:
            self.pki_manager, self.mqtt_provisioner = bootstrap_mqtt_infrastructure(
                cert_dir=self.cert_dir,
                broker_host=self.mqtt_host,
                broker_port=self.mqtt_port
            )
            return True
        except Exception as e:
            print(f"[ORCH-MQTT] Bootstrap error: {e}")
            return False

    def _check_mqtt_broker(self) -> bool:
        """Check if MQTT broker is running on TLS port."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                result = s.connect_ex((self.mqtt_host, self.mqtt_port))
                if result == 0:
                    print(f"[ORCH-MQTT] MQTT broker detected on {self.mqtt_host}:{self.mqtt_port}")
                    return True
        except Exception as e:
            print(f"[ORCH-MQTT] MQTT broker check error: {e}")

        print(f"[ORCH-MQTT] WARNING: MQTT broker not detected on {self.mqtt_host}:{self.mqtt_port}")
        return False

    def _start_broker_docker(self):
        """Start MQTT broker in Docker if available."""
        print("[ORCH-MQTT] Attempting to start MQTT broker in Docker...")

        # Check Docker availability
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("[ORCH-MQTT] Docker not available; MQTT broker must be running manually")
            return False

        # Create mosquitto config and certs in container
        config_content = """
listener 1883
protocol mqtt

listener 8883
protocol mqtt
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/mosquitto.crt
keyfile /mosquitto/certs/mosquitto.key
require_certificate true

persistence true
persistence_location /mosquitto/data/
log_dest stdout
"""

        config_path = Path(self.cert_dir) / "mosquitto.conf"
        config_path.write_text(config_content)

        try:
            # Stop existing container
            subprocess.run(["docker", "stop", "dslab-mosquitto"], capture_output=True)
            subprocess.run(["docker", "rm", "dslab-mosquitto"], capture_output=True)
        except:
            pass

        # Start new container
        cmd = [
            "docker", "run", "-d",
            "--name", "dslab-mosquitto",
            "-p", f"{self.mqtt_plaintext_port}:1883",
            "-p", f"{self.mqtt_port}:8883",
            "-v", f"{Path(self.cert_dir).absolute()}:/mosquitto/certs",
            "-v", f"{config_path.absolute()}:/mosquitto/config/mosquitto.conf",
            "eclipse-mosquitto:latest"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"[ORCH-MQTT] MQTT broker started in Docker (container ID: {result.stdout.strip()[:12]})")
            time.sleep(3)  # Wait for broker to be ready
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ORCH-MQTT] Failed to start Docker MQTT: {e.stderr}")
            return False

    def _start_service(self, service_name: str, module_path: str, env_vars: dict = None):
        """Start a service in a background process."""
        cmd = [sys.executable, "-m", module_path]
        print(f"[ORCH-MQTT] Starting {service_name}: {' '.join(cmd)}")

        # Setup environment
        env = os.environ.copy()
        env["MQTT_HOST"] = self.mqtt_host
        env["MQTT_PORT"] = str(self.mqtt_port)
        env["CERT_DIR"] = self.cert_dir

        if env_vars:
            env.update(env_vars)

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )
            self.processes[service_name] = proc
            print(f"[ORCH-MQTT] {service_name} launched (PID: {proc.pid})")
        except Exception as e:
            print(f"[ORCH-MQTT] ERROR starting {service_name}: {e}")

    def _start_broker_native(self):
        """Start mosquitto broker natively (Linux/MacOS only)."""
        config_path = Path(self.cert_dir) / "mosquitto.conf"

        try:
            proc = subprocess.Popen(
                ["mosquitto", "-c", str(config_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.processes["mosquitto-broker"] = proc
            print(f"[ORCH-MQTT] Mosquitto broker started (PID: {proc.pid})")
            time.sleep(2)
            return True
        except FileNotFoundError:
            print("[ORCH-MQTT] Mosquitto not found in PATH")
            return False
        except Exception as e:
            print(f"[ORCH-MQTT] Failed to start mosquitto: {e}")
            return False

    def start_all(self):
        """Start all services with MQTT + PKI."""
        print("=" * 80)
        print("SMART CITY MQTT DISTRIBUTED SERVICES ORCHESTRATOR")
        print("=" * 80)

        # Bootstrap PKI + MQTT infrastructure
        if not self._bootstrap_mqtt_infrastructure():
            print("[ORCH-MQTT] CRITICAL: Failed to bootstrap MQTT infrastructure")
            return False

        time.sleep(1)

        # Check/start MQTT broker
        if not self._check_mqtt_broker():
            print("[ORCH-MQTT] Attempting to start MQTT broker...")

            # Try Docker first
            if not self._start_broker_docker():
                # Try native mosquitto
                if not self._start_broker_native():
                    print("[ORCH-MQTT] Could not start MQTT broker automatically")
                    print("[ORCH-MQTT] Please start mosquitto or Docker manually:")
                    print(f"  Docker:  docker run -d --name mosquitto -p {self.mqtt_plaintext_port}:1883 -p {self.mqtt_port}:8883 eclipse-mosquitto")
                    print(f"  Native:  mosquitto -c {self.cert_dir}/mosquitto.conf")
                    return False

        time.sleep(2)

        # Launch services
        print("[ORCH-MQTT] Launching services with MQTT...")

        self._start_service("vehicle-service", "services.vehicle_service")
        time.sleep(2)

        self._start_service("fog-service", "services.fog_service")
        time.sleep(2)

        self._start_service("cloud-service", "services.cloud_service")
        time.sleep(3)

        print("\n" + "=" * 80)
        print("MQTT SERVICE STARTUP COMPLETE")
        print("=" * 80)

        print("\nServices running:")
        for name in self.processes:
            proc = self.processes[name]
            if proc.poll() is None:
                print(f"  [OK]  {name} (PID: {proc.pid})")
            else:
                print(f"  ✗ {name} (FAILED)")

        print("\nEndpoints:")
        print(f"  - Flask API:    http://127.0.0.1:5000")
        print(f"  - WebSocket:    ws://127.0.0.1:8765")
        print(f"  - MQTT Plain:   mqtt://{self.mqtt_host}:{self.mqtt_plaintext_port}")
        print(f"  - MQTT mTLS:    mqtts://{self.mqtt_host}:{self.mqtt_port}")
        print(f"  - Certs:        ./{self.cert_dir}/")

        print("\nProvisioned services:")
        if self.mqtt_provisioner:
            for svc in self.mqtt_provisioner.list_provisioned_services():
                print(f"  [OK]  {svc}")

        print("\nPress Ctrl+C to stop all services...\n")

        # Wait for all processes
        try:
            # Monitor processes
            while True:
                time.sleep(1)
                all_running = all(proc.poll() is None for proc in self.processes.values())
                if not all_running:
                    # At least one process died
                    for name, proc in self.processes.items():
                        if proc.poll() is not None:
                            print(f"[ORCH-MQTT] Service {name} exited with code {proc.returncode}")
                    break

        except KeyboardInterrupt:
            print("\n[ORCH-MQTT] Stopping all services...")
            self.stop_all()

    def stop_all(self):
        """Stop all running services."""
        for service_name, proc in self.processes.items():
            if proc.poll() is None:  # Still running
                print(f"[ORCH-MQTT] Terminating {service_name} (PID: {proc.pid})...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"[ORCH-MQTT] Force kill {service_name}")
                    proc.kill()

        print("[ORCH-MQTT] All services stopped")

        # Stop Docker broker if we started it
        try:
            subprocess.run(["docker", "stop", "dslab-mosquitto"], capture_output=True, timeout=5)
        except:
            pass

    def export_deployment_bundle(self):
        """Export all artifacts for deployment."""
        if not self.mqtt_provisioner:
            return False

        bundle_path = self.mqtt_provisioner.export_cert_bundle("mqtt-deployment-bundle.tar.gz")
        print(f"[ORCH-MQTT] Deployment bundle exported to {bundle_path}")
        return True

    def status(self):
        """Print infrastructure status."""
        print("\n[ORCH-MQTT] Infrastructure Status:")
        if self.mqtt_provisioner:
            status = self.mqtt_provisioner.status()
            for key, val in status.items():
                print(f"  {key}: {val}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MQTT Service Orchestrator")
    parser.add_argument("--mqtt-host", default="localhost", help="MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, default=8883, help="MQTT broker TLS port")
    parser.add_argument("--mqtt-plaintext-port", type=int, default=1883, help="MQTT broker plaintext port")
    parser.add_argument("--cert-dir", default="certs", help="Certificate directory")
    parser.add_argument("--skip-broker", action="store_true", help="Skip broker startup (already running)")
    parser.add_argument("--status", action="store_true", help="Print status only")

    args = parser.parse_args()

    orch = MQTTServiceOrchestrator(
        cert_dir=args.cert_dir,
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        mqtt_plaintext_port=args.mqtt_plaintext_port,
        start_broker=not args.skip_broker
    )

    if args.status:
        # Quick bootstrap for status
        orch._bootstrap_mqtt_infrastructure()
        orch.status()
    else:
        orch.start_all()
