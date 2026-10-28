from dataclasses import dataclass
from typing import Dict


@dataclass
class DeviceIdentity:
    device_id: str
    role: str
    cert_fingerprint: str


class IdentityRegistry:
    """Lightweight identity registry for least-privilege role checks."""

    def __init__(self):
        self._identities: Dict[str, DeviceIdentity] = {}

    def register(self, identity: DeviceIdentity):
        self._identities[identity.device_id] = identity

    def is_allowed(self, device_id: str, required_role: str) -> bool:
        identity = self._identities.get(device_id)
        if not identity:
            return False
        return identity.role == required_role
