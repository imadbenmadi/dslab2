"""
Service Orchestrator - Launches all three services with proper setup.
Handles certificate generation, NATS broker, and service startup.

Run: python -m services.orchestrator
"""

import subprocess
import sys
import time
import os
from pathlib import Path

from infrastructure.cert_manager import CertificateManager


class ServiceOrchestrator:
    """Orchestrate startup of all three distributed services."""

    def __init__(self, cert_dir: str = "certs", nats_url: str = "nats://localhost:4222"):
        self.cert_dir = cert_dir
        self.nats_url = nats_url
        self.processes = {}

    def _ensure_certificates(self):
        """Generate mTLS certificates if not present."""
        print("[ORCH] Generating mTLS certificates...")
        mgr = CertificateManager(self.cert_dir)
        mgr.get_or_create_certs()
        print(f"[ORCH] Certificates ready in {self.cert_dir}/")

    def _check_nats_broker(self):
        """Check if NATS broker is running."""
        import socket
        try:
            host, port = "127.0.0.1", 4222
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex((host, port))
                if result == 0:
                    print(f"[ORCH] NATS broker running on {host}:{port}")
                    return True
        except Exception as e:
            print(f"[ORCH] NATS check error: {e}")

        print("[ORCH] WARNING: NATS broker not detected on localhost:4222")
        print("[ORCH] Install NATS: https://docs.nats.io/running-a-nats-server/installation")
        print("[ORCH] Run: nats-server")
        return False

    def _start_service(self, service_name: str, module_path: str):
        """Start a service in a background process."""
        cmd = [sys.executable, "-m", module_path]
        print(f"[ORCH] Starting {service_name}: {' '.join(cmd)}")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            self.processes[service_name] = proc

            # Print first few lines of output
            print(f"[ORCH] {service_name} launched (PID: {proc.pid})")

            # Start output capture thread (optional)
            # threading.Thread(target=self._capture_output, args=(service_name, proc), daemon=True).start()

        except Exception as e:
            print(f"[ORCH] ERROR starting {service_name}: {e}")

    def _capture_output(self, service_name: str, proc):
        """Capture and print service output (optional)."""
        try:
            for line in proc.stdout:
                print(f"[{service_name}] {line.rstrip()}")
        except Exception as e:
            print(f"[ORCH] Output capture error for {service_name}: {e}")

    def start_all(self):
        """Start all three services."""
        print("=" * 80)
        print("SMART CITY DISTRIBUTED SERVICES ORCHESTRATOR")
        print("=" * 80)

        # Setup
        self._ensure_certificates()
        time.sleep(1)

        if not self._check_nats_broker():
            print("[ORCH] NATS broker required but not running. Attempting to skip...")
            print("[ORCH] Services will retry connection on startup.")

        time.sleep(2)

        # Launch services
        print("[ORCH] Launching services...")

        self._start_service("vehicle-service", "services.vehicle_service")
        time.sleep(2)

        self._start_service("fog-service", "services.fog_service")
        time.sleep(2)

        self._start_service("cloud-service", "services.cloud_service")
        time.sleep(3)

        print("\n" + "=" * 80)
        print("SERVICE STARTUP COMPLETE")
        print("=" * 80)
        print("\nServices running:")
        for name in self.processes:
            print(f"  ✓ {name}")

        print("\nEndpoints:")
        print(f"  - Flask API:  http://127.0.0.1:5000")
        print(f"  - WebSocket:  ws://127.0.0.1:8765")
        print(f"  - NATS:       {self.nats_url}")
        print(f"  - Certs:      ./{self.cert_dir}/")

        print("\nPress Ctrl+C to stop all services...\n")

        # Wait for all processes
        try:
            for service_name, proc in self.processes.items():
                proc.wait()
        except KeyboardInterrupt:
            print("\n[ORCH] Stopping all services...")
            self.stop_all()

    def stop_all(self):
        """Stop all running services."""
        for service_name, proc in self.processes.items():
            if proc.poll() is None:  # Still running
                print(f"[ORCH] Terminating {service_name} (PID: {proc.pid})...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"[ORCH] Force kill {service_name}")
                    proc.kill()

        print("[ORCH] All services stopped")


if __name__ == "__main__":
    orch = ServiceOrchestrator()
    orch.start_all()
