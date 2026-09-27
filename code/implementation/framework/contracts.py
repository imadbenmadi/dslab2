from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

CONTRACT_VERSION = "v1.0.0"


@dataclass
class ContractEnvelope:
    contract_version: str
    event_type: str
    event_id: str
    timestamp: str
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VehicleTaskSubmitted:
    task_id: str
    vehicle_id: str
    sim_time: float
    position: Dict[str, float]


@dataclass
class FogDecisionMade:
    task_id: str
    step_id: str
    broker_zone: str
    decision: str
    destination: str
    reason: str


@dataclass
class HandoffTriggered:
    task_id: str
    vehicle_id: str
    source_fog: str
    target_fog: str
    mode: str


@dataclass
class CloudForwarded:
    task_id: str
    ingress_fog: str
    cloud_id: str
    payload_kb: float


@dataclass
class TaskCompleted:
    task_id: str
    vehicle_id: str
    latency_ms: float
    energy_j: float
    deadline_met: bool


def make_envelope(event_type: str, event_id: str, timestamp: str, payload: Dict[str, Any]) -> ContractEnvelope:
    return ContractEnvelope(
        contract_version=CONTRACT_VERSION,
        event_type=event_type,
        event_id=event_id,
        timestamp=timestamp,
        payload=payload,
    )


def validate_envelope(envelope: Dict[str, Any]) -> Optional[str]:
    required = ["contract_version", "event_type", "event_id", "timestamp", "payload"]
    for key in required:
        if key not in envelope:
            return f"missing:{key}"
    if envelope["contract_version"] != CONTRACT_VERSION:
        return f"version_mismatch:{envelope['contract_version']}"
    if not isinstance(envelope["payload"], dict):
        return "invalid_payload"
    return None
