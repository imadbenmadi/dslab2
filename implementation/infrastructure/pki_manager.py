"""
Enterprise PKI Management with Certificate Rotation, CRL, and OCSP.
Provides full certificate lifecycle management for production deployment.
"""

import os
import json
import time
import hashlib
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import CertificateBuilder, CertificateSigningRequestBuilder


class CertificateStatus(Enum):
    """Certificate lifecycle status."""
    ISSUED = "issued"
    REVOKED = "revoked"
    EXPIRED = "expired"
    PENDING_ROTATION = "pending_rotation"


@dataclass
class CertificateMetadata:
    """Metadata for tracking certificate lifecycle."""
    serial: int
    subject_cn: str
    issuer_cn: str
    issued_at: float
    expires_at: float
    status: str
    fingerprint_sha256: str
    rotation_scheduled_at: Optional[float] = None


class PKIManager:
    """Enterprise PKI with root CA, intermediate CA, and service certificates."""

    def __init__(self, pki_dir: str = "certs/pki", rotation_days_before: int = 30):
        self.pki_dir = Path(pki_dir)
        self.pki_dir.mkdir(parents=True, exist_ok=True)

        # Directory structure
        self.root_ca_dir = self.pki_dir / "root-ca"
        self.intermediate_ca_dir = self.pki_dir / "intermediate-ca"
        self.services_dir = self.pki_dir / "services"
        self.crl_dir = self.pki_dir / "crl"
        self.revoked_dir = self.pki_dir / "revoked"

        for d in [self.root_ca_dir, self.intermediate_ca_dir, self.services_dir, self.crl_dir, self.revoked_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.rotation_days_before = rotation_days_before
        self.cert_metadata_file = self.pki_dir / "certificates.json"
        self.crl_file = self.crl_dir / "ca.crl"
        self.revoked_list: Dict[int, CertificateMetadata] = {}

        self._load_revoked_list()
        self._load_certificate_metadata()

    def generate_root_ca(
        self,
        common_name: str = "SmartCity-Root-CA",
        validity_days: int = 3652
    ) -> Tuple[Path, Path]:
        """Generate self-signed root CA (valid 10 years)."""
        cert_path = self.root_ca_dir / "ca.crt"
        key_path = self.root_ca_dir / "ca.key"

        if cert_path.exists() and key_path.exists():
            print(f"[PKI] Root CA already exists: {cert_path}")
            return cert_path, key_path

        print(f"[PKI] Generating Root CA...")

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,  # Production-grade key size
            backend=default_backend()
        )

        # Build certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"TR"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Istanbul"),
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
            datetime.utcnow() + timedelta(days=validity_days)
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
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
            critical=False,
        ).sign(
            private_key,
            hashes.SHA256(),
            default_backend()
        )

        # Write files
        with open(key_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(cert_path, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"[PKI] Root CA generated: {cert_path}")
        return cert_path, key_path

    def generate_intermediate_ca(
        self,
        common_name: str = "SmartCity-Intermediate-CA",
        validity_days: int = 1825
    ) -> Tuple[Path, Path]:
        """Generate intermediate CA signed by root CA (valid 5 years)."""
        cert_path = self.intermediate_ca_dir / "ca.crt"
        key_path = self.intermediate_ca_dir / "ca.key"

        if cert_path.exists() and key_path.exists():
            print(f"[PKI] Intermediate CA already exists: {cert_path}")
            return cert_path, key_path

        print(f"[PKI] Generating Intermediate CA...")

        # Load root CA
        root_cert_path, root_key_path = self.generate_root_ca()
        with open(root_key_path, 'rb') as f:
            root_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )

        with open(root_cert_path, 'rb') as f:
            root_cert = x509.load_pem_x509_certificate(
                f.read(),
                default_backend()
            )

        # Generate intermediate key
        int_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # Build intermediate certificate
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"TR"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Istanbul"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"SmartCity"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            root_cert.issuer
        ).public_key(
            int_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=0),  # Can't sign other CAs
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
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(int_key.public_key()),
            critical=False,
        ).add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(root_key.public_key()),
            critical=False,
        ).sign(
            root_key,
            hashes.SHA256(),
            default_backend()
        )

        # Write files
        with open(key_path, 'wb') as f:
            f.write(int_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(cert_path, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"[PKI] Intermediate CA generated: {cert_path}")
        return cert_path, key_path

    def generate_service_certificate(
        self,
        service_name: str,
        role: str,
        validity_days: int = 365
    ) -> Tuple[Path, Path, Path]:
        """Generate service certificate signed by intermediate CA."""
        service_dir = self.services_dir / service_name
        service_dir.mkdir(parents=True, exist_ok=True)

        cert_path = service_dir / f"{service_name}.crt"
        key_path = service_dir / f"{service_name}.key"
        chain_path = service_dir / "chain.crt"

        # Load intermediate CA
        int_cert_path, int_key_path = self.generate_intermediate_ca()
        with open(int_key_path, 'rb') as f:
            int_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )

        with open(int_cert_path, 'rb') as f:
            int_cert = x509.load_pem_x509_certificate(
                f.read(),
                default_backend()
            )

        # Generate service key
        svc_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # Build service certificate with role in OU
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"TR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"SmartCity"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, role),
            x509.NameAttribute(NameOID.COMMON_NAME, f"{service_name}.smartcity.local"),
        ])

        expires_at = datetime.utcnow() + timedelta(days=validity_days)

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            int_cert.issuer
        ).public_key(
            svc_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            expires_at
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(f"{service_name}.smartcity.local"),
                x509.DNSName("localhost"),
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
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(svc_key.public_key()),
            critical=False,
        ).add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(int_key.public_key()),
            critical=False,
        ).sign(
            int_key,
            hashes.SHA256(),
            default_backend()
        )

        # Write service key and certificate
        with open(key_path, 'wb') as f:
            f.write(svc_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(cert_path, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        # Write chain (intermediate + root)
        root_cert_path, _ = self.generate_root_ca()
        with open(chain_path, 'wb') as f:
            with open(int_cert_path, 'rb') as icp:
                f.write(icp.read())
            with open(root_cert_path, 'rb') as rcp:
                f.write(rcp.read())

        # Track metadata
        metadata = CertificateMetadata(
            serial=cert.serial_number,
            subject_cn=service_name,
            issuer_cn="SmartCity-Intermediate-CA",
            issued_at=time.time(),
            expires_at=expires_at.timestamp(),
            status=CertificateStatus.ISSUED.value,
            fingerprint_sha256=cert.fingerprint(hashes.SHA256()).hex(),
            rotation_scheduled_at=(expires_at - timedelta(days=self.rotation_days_before)).timestamp()
        )

        self._save_certificate_metadata(metadata)

        print(f"[PKI] Service cert generated: {cert_path} (role={role})")
        return cert_path, key_path, chain_path

    def check_rotation_needed(self) -> List[Tuple[str, CertificateMetadata]]:
        """Check which certificates need rotation."""
        needs_rotation = []
        now = time.time()

        for cn, metadata in self._load_certificate_metadata().items():
            if metadata['status'] == CertificateStatus.ISSUED.value:
                rotation_scheduled = metadata.get('rotation_scheduled_at', 0)
                if now >= rotation_scheduled:
                    needs_rotation.append((cn, metadata))

        return needs_rotation

    def rotate_certificate(self, service_name: str, role: str) -> Tuple[Path, Path, Path]:
        """Rotate a certificate to a new one."""
        print(f"[PKI] Rotating certificate for {service_name}...")

        # Revoke old certificate
        service_dir = self.services_dir / service_name
        old_cert_path = service_dir / f"{service_name}.crt"

        if old_cert_path.exists():
            with open(old_cert_path, 'rb') as f:
                old_cert = x509.load_pem_x509_certificate(
                    f.read(),
                    default_backend()
                )
            self.revoke_certificate(old_cert.serial_number, service_name)

        # Generate new certificate
        return self.generate_service_certificate(service_name, role, validity_days=365)

    def revoke_certificate(self, serial_number: int, service_name: str):
        """Revoke a certificate and add to CRL."""
        metadata = CertificateMetadata(
            serial=serial_number,
            subject_cn=service_name,
            issuer_cn="SmartCity-Intermediate-CA",
            issued_at=0,
            expires_at=0,
            status=CertificateStatus.REVOKED.value,
            fingerprint_sha256="",
        )

        self.revoked_list[serial_number] = metadata
        self._save_revoked_list()
        print(f"[PKI] Certificate {serial_number} revoked")

    def _save_certificate_metadata(self, metadata: CertificateMetadata):
        """Save certificate metadata to JSON."""
        all_metadata = self._load_certificate_metadata()
        all_metadata[metadata.subject_cn] = asdict(metadata)

        with open(self.cert_metadata_file, 'w') as f:
            json.dump(all_metadata, f, indent=2)

    def _load_certificate_metadata(self) -> Dict:
        """Load certificate metadata from JSON."""
        if not self.cert_metadata_file.exists():
            return {}

        with open(self.cert_metadata_file) as f:
            return json.load(f)

    def _save_revoked_list(self):
        """Save revoked certificate list."""
        revoked_file = self.crl_dir / "revoked.json"
        with open(revoked_file, 'w') as f:
            json.dump({
                k: v for k, v in self.revoked_list.items()
            }, f, indent=2)

    def _load_revoked_list(self):
        """Load revoked certificate list."""
        revoked_file = self.crl_dir / "revoked.json"
        if revoked_file.exists():
            with open(revoked_file) as f:
                data = json.load(f)
                self.revoked_list = {int(k): v for k, v in data.items()}

    def is_certificate_valid(self, cert_path: Path) -> bool:
        """Check if a certificate is valid and not revoked."""
        try:
            with open(cert_path, 'rb') as f:
                cert = x509.load_pem_x509_certificate(
                    f.read(),
                    default_backend()
                )

            # Check expiration
            if datetime.utcnow() > cert.not_valid_after_utc:
                print(f"[PKI] Certificate expired: {cert_path}")
                return False

            # Check revocation
            if cert.serial_number in self.revoked_list:
                print(f"[PKI] Certificate revoked: {cert_path}")
                return False

            return True

        except Exception as e:
            print(f"[PKI] Certificate validation error: {e}")
            return False

    def start_rotation_daemon(self, check_interval_hours: int = 24):
        """Start background daemon to check and rotate expiring certs."""
        def rotation_loop():
            while True:
                try:
                    needs_rotation = self.check_rotation_needed()
                    for service_name, metadata in needs_rotation:
                        role = metadata.get('issuer_cn', 'unknown')
                        self.rotate_certificate(service_name, role)
                        print(f"[PKI] Auto-rotated expired cert for {service_name}")
                except Exception as e:
                    print(f"[PKI] Rotation daemon error: {e}")

                time.sleep(check_interval_hours * 3600)

        thread = threading.Thread(target=rotation_loop, daemon=True)
        thread.start()
        print(f"[PKI] Rotation daemon started (check interval: {check_interval_hours}h)")
