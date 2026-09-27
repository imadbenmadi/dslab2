"""
mTLS Certificate Generation and Management for Distributed Services.
Supports service-level mTLS with role-based authorization.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from typing import Dict, Tuple


class CertificateManager:
    """Generate and manage mTLS certificates for services."""

    def __init__(self, cert_dir: str = "certs"):
        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(exist_ok=True)

    def generate_ca_cert(self, common_name: str = "Smart-City-CA") -> Tuple[Path, Path]:
        """Generate self-signed CA certificate."""
        ca_cert_path = self.cert_dir / "ca.crt"
        ca_key_path = self.cert_dir / "ca.key"

        if ca_cert_path.exists() and ca_key_path.exists():
            return ca_cert_path, ca_key_path

        # Generate CA key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # Generate CA certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"TR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"SmartCity"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=3652)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).sign(
            private_key,
            hashes.SHA256(),
            default_backend()
        )

        # Write CA key
        with open(ca_key_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        # Write CA cert
        with open(ca_cert_path, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"[CERT] CA generated: {ca_cert_path}")
        return ca_cert_path, ca_key_path

    def generate_service_cert(
        self,
        service_name: str,
        role: str,
        ca_cert_path: Path,
        ca_key_path: Path
    ) -> Tuple[Path, Path]:
        """Generate service certificate signed by CA."""
        cert_path = self.cert_dir / f"{service_name}.crt"
        key_path = self.cert_dir / f"{service_name}.key"

        if cert_path.exists() and key_path.exists():
            return cert_path, key_path

        # Load CA
        with open(ca_key_path, 'rb') as f:
            ca_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )

        with open(ca_cert_path, 'rb') as f:
            ca_cert = x509.load_pem_x509_certificate(
                f.read(),
                default_backend()
            )

        # Generate service key
        svc_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # Build subject with role in CN
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"TR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"SmartCity"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, role),
            x509.NameAttribute(NameOID.COMMON_NAME, f"{service_name}.smartcity.local"),
        ])

        # Build certificate
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            ca_cert.issuer
        ).public_key(
            svc_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(f"{service_name}.smartcity.local"),
                x509.DNSName("localhost"),
                x509.DNSName("127.0.0.1"),
            ]),
            critical=False,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        ).sign(
            ca_key,
            hashes.SHA256(),
            default_backend()
        )

        # Write service key
        with open(key_path, 'wb') as f:
            f.write(svc_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        # Write service cert
        with open(cert_path, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"[CERT] Service cert generated: {cert_path} (role={role})")
        return cert_path, key_path

    def get_or_create_certs(self) -> Dict[str, Dict[str, str]]:
        """Generate all service certificates."""
        ca_cert, ca_key = self.generate_ca_cert()

        services = {
            "vehicle-service": "vehicle",
            "fog-service": "fog",
            "cloud-service": "cloud",
        }

        certs = {}
        for service_name, role in services.items():
            cert_path, key_path = self.generate_service_cert(
                service_name,
                role,
                ca_cert,
                ca_key
            )
            certs[service_name] = {
                "cert": str(cert_path),
                "key": str(key_path),
                "ca": str(ca_cert),
                "role": role,
            }

        # Write cert index
        index_path = self.cert_dir / "certs.json"
        with open(index_path, 'w') as f:
            json.dump(certs, f, indent=2)

        return certs


def get_mtls_config(service_name: str, cert_dir: str = "certs") -> Dict[str, str]:
    """Load mTLS config for a service."""
    index_path = Path(cert_dir) / "certs.json"
    if not index_path.exists():
        mgr = CertificateManager(cert_dir)
        mgr.get_or_create_certs()

    with open(index_path) as f:
        certs = json.load(f)

    if service_name not in certs:
        raise ValueError(f"Service {service_name} not found in certificate index")

    return certs[service_name]
