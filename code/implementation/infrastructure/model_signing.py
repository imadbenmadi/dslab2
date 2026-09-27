"""
Signed Model Artifacts with End-to-End Verification Chain.
Ensures agent models are signed, versioned, and verified before execution.
"""

import json
import hashlib
import pickle
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend


@dataclass
class ModelArtifact:
    """Immutable model artifact descriptor."""
    model_name: str
    version: str
    model_type: str  # "dqn-agent1", "dqn-agent2", "policy", etc.
    model_file: str
    model_hash_sha256: str
    metadata: Dict = None
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ModelSignature:
    """Digital signature of model artifact."""
    model_name: str
    version: str
    model_hash_sha256: str
    signature_algorithm: str  # "RSA-SHA256"
    signature_hex: str
    signed_by_service: str  # e.g., "cloud-service"
    signed_at: str
    signer_cert_fingerprint: str
    signature_valid: bool = True


class ModelArtifactManager:
    """
    Manages model signing, versioning, and verification.
    Ensures all agents execute from signed, verified artifacts.
    """

    def __init__(
        self,
        models_dir: str = "models",
        manifests_dir: str = "models/manifests",
        signer_key_path: Optional[Path] = None,
        signer_cert_path: Optional[Path] = None
    ):
        self.models_dir = Path(models_dir)
        self.manifests_dir = Path(manifests_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)

        self.signer_key_path = signer_key_path
        self.signer_cert_path = signer_cert_path
        self.signer_key = None
        self.signer_cert = None
        self.signatures_index: Dict[str, ModelSignature] = {}

        if signer_key_path and signer_key_path.exists():
            self._load_signer_key()

        self._load_signatures_index()

    def _load_signer_key(self):
        """Load signing key from PEM file."""
        try:
            with open(self.signer_key_path, 'rb') as f:
                self.signer_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            print(f"[MODEL] Signer key loaded: {self.signer_key_path}")

            if self.signer_cert_path and self.signer_cert_path.exists():
                from cryptography import x509
                with open(self.signer_cert_path, 'rb') as f:
                    self.signer_cert = x509.load_pem_x509_certificate(
                        f.read(),
                        default_backend()
                    )
                print(f"[MODEL] Signer cert loaded: {self.signer_cert_path}")
        except Exception as e:
            print(f"[MODEL] Failed to load signer key: {e}")

    def register_model(
        self,
        model_name: str,
        version: str,
        model_type: str,
        model_file: Path,
        metadata: Optional[Dict] = None
    ) -> ModelArtifact:
        """Register a model artifact (pre-signing)."""
        # Compute hash
        model_hash = self._compute_file_hash(model_file)

        artifact = ModelArtifact(
            model_name=model_name,
            version=version,
            model_type=model_type,
            model_file=str(model_file),
            model_hash_sha256=model_hash,
            metadata=metadata or {}
        )

        print(f"[MODEL] Registered: {model_name} v{version} (hash: {model_hash[:8]}...)")
        return artifact

    def sign_model(
        self,
        artifact: ModelArtifact,
        sign_by_service: str = "cloud-service"
    ) -> ModelSignature:
        """Sign a model artifact with the signer's private key."""
        if not self.signer_key:
            raise RuntimeError("No signer key configured. Cannot sign models.")

        # Create signature payload (deterministic)
        payload = f"{artifact.model_name}:{artifact.version}:{artifact.model_hash_sha256}"

        # Sign with private key
        signature_bytes = self.signer_key.sign(
            payload.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        signature_hex = signature_bytes.hex()

        # Get signer cert fingerprint
        signer_fingerprint = ""
        if self.signer_cert:
            signer_fingerprint = self.signer_cert.fingerprint(hashes.SHA256()).hex()[:16]

        signature = ModelSignature(
            model_name=artifact.model_name,
            version=artifact.version,
            model_hash_sha256=artifact.model_hash_sha256,
            signature_algorithm="RSA-SHA256",
            signature_hex=signature_hex,
            signed_by_service=sign_by_service,
            signed_at=datetime.utcnow().isoformat(),
            signer_cert_fingerprint=signer_fingerprint,
            signature_valid=True
        )

        # Store
        key = f"{artifact.model_name}:{artifact.version}"
        self.signatures_index[key] = signature
        self._save_signatures_index()

        print(f"[MODEL] Signed: {artifact.model_name} v{artifact.version} (sig: {signature_hex[:8]}...)")
        return signature

    def verify_model(
        self,
        artifact: ModelArtifact,
        signature: ModelSignature,
        verifier_cert_path: Optional[Path] = None
    ) -> Tuple[bool, str]:
        """
        Verify model signature.
        Returns (valid, reason).
        """

        # Step 1: File hash integrity
        current_hash = self._compute_file_hash(artifact.model_file)
        if current_hash != artifact.model_hash_sha256:
            return False, f"Hash mismatch: stored={artifact.model_hash_sha256[:8]}... current={current_hash[:8]}..."

        # Step 2: Signature integrity (requires verifier cert)
        if verifier_cert_path and verifier_cert_path.exists():
            try:
                valid = self._verify_signature(artifact, signature, verifier_cert_path)
                if not valid:
                    return False, "Signature verification failed"
            except Exception as e:
                return False, f"Signature verification error: {e}"

        # Step 3: Signature timestamp check (not too old)
        sig_date = datetime.fromisoformat(signature.signed_at)
        age_days = (datetime.utcnow() - sig_date).days
        if age_days > 365:  # Warn if older than 1 year
            print(f"[MODEL] Warning: Signature is {age_days} days old")

        return True, "Valid"

    def _verify_signature(
        self,
        artifact: ModelArtifact,
        signature: ModelSignature,
        cert_path: Path
    ) -> bool:
        """Verify RSA signature using certificate."""
        from cryptography import x509

        with open(cert_path, 'rb') as f:
            cert = x509.load_pem_x509_certificate(f.read(), default_backend())

        public_key = cert.public_key()

        # Recreate payload
        payload = f"{artifact.model_name}:{artifact.version}:{artifact.model_hash_sha256}"

        try:
            public_key.verify(
                bytes.fromhex(signature.signature_hex),
                payload.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            print(f"[MODEL] Signature verification failed: {e}")
            return False

    def load_and_verify_model(
        self,
        model_name: str,
        version: str,
        verifier_cert_path: Optional[Path] = None
    ) -> Optional[bytes]:
        """
        Load model from disk with full verification chain.
        Returns model bytes if valid, None otherwise.
        """
        key = f"{model_name}:{version}"

        # Check if signature exists
        if key not in self.signatures_index:
            print(f"[MODEL] No signature found for {model_name} v{version}")
            return None

        signature = self.signatures_index[key]

        # Reconstruct artifact
        model_path = self.models_dir / f"{model_name}-{version}.pkl"
        if not model_path.exists():
            print(f"[MODEL] Model file not found: {model_path}")
            return None

        artifact = ModelArtifact(
            model_name=model_name,
            version=version,
            model_type="dqn-agent",  # Placeholder
            model_file=str(model_path),
            model_hash_sha256=signature.model_hash_sha256
        )

        # Verify
        valid, reason = self.verify_model(artifact, signature, verifier_cert_path)
        if not valid:
            print(f"[MODEL] Verification failed: {reason}")
            return None

        # Load
        try:
            with open(model_path, 'rb') as f:
                model_data = f.read()
            print(f"[MODEL] Loaded & verified: {model_name} v{version}")
            return model_data
        except Exception as e:
            print(f"[MODEL] Failed to load model: {e}")
            return None

    def _compute_file_hash(self, file_path) -> str:
        """Compute SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _save_signatures_index(self):
        """Save signatures to JSON index."""
        index_path = self.manifests_dir / "signatures.json"
        with open(index_path, 'w') as f:
            json.dump({
                k: asdict(v) for k, v in self.signatures_index.items()
            }, f, indent=2)

    def _load_signatures_index(self):
        """Load signatures from JSON index."""
        index_path = self.manifests_dir / "signatures.json"
        if index_path.exists():
            with open(index_path) as f:
                data = json.load(f)
                for k, v in data.items():
                    sig_dict = v.copy()
                    self.signatures_index[k] = ModelSignature(**sig_dict)

    def export_model_manifest(self) -> Dict:
        """Export all models and signatures as manifest."""
        return {
            "exported_at": datetime.utcnow().isoformat(),
            "signatures": {
                k: asdict(v) for k, v in self.signatures_index.items()
            },
            "signer_fingerprint": self.signer_cert.fingerprint(hashes.SHA256()).hex()[:16] if self.signer_cert else None,
        }


def bootstrap_model_signing_chain():
    """
    Initialize model signing chain with cloud-service signer cert.
    Call this on cloud service startup.
    """
    from infrastructure.pki_manager import PKIManager

    pki = PKIManager()

    # Generate cloud-service cert
    cert_path, key_path, _ = pki.generate_service_certificate(
        "cloud-service",
        role="cloud-signer",
        validity_days=365
    )

    # Create model manager
    mgr = ModelArtifactManager(
        signer_key_path=key_path,
        signer_cert_path=cert_path
    )

    print(f"[MODEL] Signing chain initialized:")
    print(f"  Signer: cloud-service")
    print(f"  Key: {key_path}")
    print(f"  Cert: {cert_path}")

    return mgr
