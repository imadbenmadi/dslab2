"""
Setup verification and quick-start helper for distributed services.

Run: python check_setup.py
"""

import subprocess
import sys
import os
import json
from pathlib import Path
from importlib.util import find_spec


def check_python_packages():
    """Check if required Python packages are installed."""
    print("=" * 60)
    print("CHECKING PYTHON PACKAGES")
    print("=" * 60)

    required = {
        "nats": "nats-py (NATS client)",
        "cryptography": "cryptography (mTLS certs)",
        "flask": "flask (REST API)",
        "websockets": "websockets (WebSocket)",
        "torch": "torch (DQN agents)",
        "pymoo": "pymoo (NSGA-II optimizer)",
    }

    missing = []
    for module, name in required.items():
        if find_spec(module):
            print(f"[OK]  {name}")
        else:
            print(f"✗ {name} MISSING")
            missing.append(module)

    if missing:
        print(f"\nInstall missing packages:")
        print(f"  pip install {' '.join(missing)}")
        return False
    return True


def check_nats_broker():
    """Check if NATS broker is running."""
    print("\n" + "=" * 60)
    print("CHECKING NATS BROKER")
    print("=" * 60)

    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(("127.0.0.1", 4222))
            if result == 0:
                print("[OK]  NATS broker running on localhost:4222")
                return True
    except Exception as e:
        print(f"✗ Connection check failed: {e}")

    print("✗ NATS broker NOT running on localhost:4222")
    print("\nTo start NATS:")
    print("  # Option 1: Docker")
    print("    docker run -d --name nats -p 4222:4222 nats:latest")
    print("\n  # Option 2: Direct")
    print("    nats-server")
    print("\n  (https://docs.nats.io/running-a-nats-server/installation)")
    return False


def check_certificates():
    """Check if mTLS certificates exist."""
    print("\n" + "=" * 60)
    print("CHECKING mTLS CERTIFICATES")
    print("=" * 60)

    cert_dir = Path("certs")
    required_files = [
        "ca.crt",
        "ca.key",
        "vehicle-service.crt",
        "vehicle-service.key",
        "fog-service.crt",
        "fog-service.key",
        "cloud-service.crt",
        "cloud-service.key",
        "certs.json",
    ]

    missing = []
    for file in required_files:
        file_path = cert_dir / file
        if file_path.exists():
            print(f"[OK]  {file}")
        else:
            print(f"✗ {file} MISSING")
            missing.append(file)

    if missing:
        print(f"\nGenerating certificates...")
        try:
            from infrastructure.cert_manager import CertificateManager
            mgr = CertificateManager("certs")
            mgr.get_or_create_certs()
            print("[OK]  Certificates generated successfully")
            return True
        except Exception as e:
            print(f"✗ Certificate generation failed: {e}")
            return False

    print("[OK]  All certificates present")
    return True


def check_directories():
    """Check if required directories exist."""
    print("\n" + "=" * 60)
    print("CHECKING DIRECTORIES")
    print("=" * 60)

    required_dirs = [
        "services",
        "infrastructure",
        "framework",
        "agents",
        "broker",
        "sdn",
        "results/logs",
        "certs",
    ]

    all_ok = True
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"[OK]  {dir_name}/")
        else:
            print(f"✗ {dir_name}/ MISSING")
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  Created: {dir_name}/")

    return all_ok


def show_status():
    """Display overall system status."""
    print("\n" + "=" * 60)
    print("SYSTEM STATUS")
    print("=" * 60)

    checks = [
        ("Python Packages", check_python_packages),
        ("Directories", check_directories),
        ("mTLS Certificates", check_certificates),
        ("NATS Broker", check_nats_broker),
    ]

    results = []
    for name, check_fn in checks:
        try:
            result = check_fn()
            results.append((name, result))
        except Exception as e:
            print(f"ERROR in {name}: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for name, result in results:
        status = "[OK]  OK" if result else "✗ FAILED"
        print(f"{name:.<40} {status}")

    all_ok = all(result for _, result in results)
    return all_ok


def show_next_steps():
    """Display next steps."""
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)

    print("\n1. Start NATS broker (if not already running):")
    print("   docker run -d --name nats -p 4222:4222 nats:latest")

    print("\n2. Start services:")
    print("   python -m services.orchestrator")

    print("\n3. In another terminal, start frontend:")
    print("   cd frontend && npm start")

    print("\n4. Open dashboard:")
    print("   http://localhost:3000")

    print("\n5. Check API health:")
    print("   curl http://127.0.0.1:5000/api/health")

    print("\n6. Monitor NATS topics (in separate terminal):")
    print("   nats sub telemetry.>")

    print("\nFor more info:")
    print("  - Architecture: DISTRIBUTED_ARCHITECTURE.md")
    print("  - Contracts: SERVICE_CONTRACTS.md")
    print("  - API Endpoints: README.md")


if __name__ == "__main__":
    try:
        all_ok = show_status()

        if all_ok:
            print("\n[OK]  All checks passed! System is ready.")
            show_next_steps()
        else:
            print("\n✗ Some checks failed. Please fix the issues above.")
            show_next_steps()

    except KeyboardInterrupt:
        print("\n\nSetup check interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
