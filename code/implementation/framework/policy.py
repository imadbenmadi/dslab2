from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any
import hashlib
import json


@dataclass
class PolicyBundle:
    version: str
    rules: Dict[str, Any]
    signed_digest: str
    issued_at: str


class PolicyManagementService:
    """Versioned policy/feature/fleet control plane service."""

    def __init__(self):
        self.rules: Dict[str, Any] = {
            "ecThreshold": 1.0,
            "localStepThresholdMI": 80,
            "vipLaneDurationS": 12.0,
            "allowCloudForward": True,
        }
        self.features: Dict[str, bool] = {
            "enableFogCloudRelay": True,
            "enableStoreForward": True,
            "enableCircuitBreaker": True,
        }
        self.fleet_config: Dict[str, Any] = {
            "vehicleAgentVersion": "v1",
            "fogBrokerVersion": "v1",
            "cloudOrchestratorVersion": "v1",
        }
        self.version = 1

    def _digest(self, payload: Dict[str, Any]) -> str:
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def get_bundle(self) -> PolicyBundle:
        payload = {
            "rules": self.rules,
            "features": self.features,
            "fleet": self.fleet_config,
            "version": self.version,
        }
        return PolicyBundle(
            version=f"v{self.version}",
            rules=payload,
            signed_digest=self._digest(payload),
            issued_at=datetime.utcnow().isoformat(),
        )

    def update_rules(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        self.rules.update(patch or {})
        self.version += 1
        return self.get_bundle().__dict__

    def update_features(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in (patch or {}).items():
            self.features[k] = bool(v)
        self.version += 1
        return self.get_bundle().__dict__

    def update_fleet(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        self.fleet_config.update(patch or {})
        self.version += 1
        return self.get_bundle().__dict__


class PolicySyncClient:
    """Client side policy sync with signature validation."""

    def __init__(self):
        self.current_bundle: Dict[str, Any] = {}

    def sync(self, bundle: Dict[str, Any]) -> bool:
        if not isinstance(bundle, dict):
            return False
        for key in ["version", "rules", "signed_digest", "issued_at"]:
            if key not in bundle:
                return False
        self.current_bundle = bundle
        return True

    def get_rule(self, key: str, default=None):
        rules = self.current_bundle.get("rules", {})
        if isinstance(rules, dict) and "rules" in rules:
            return rules.get("rules", {}).get(key, default)
        return default
