from typing import Dict, Any

from broker.tof_broker import TOFBroker


class TofLiteVehicleBroker:
    """Vehicle-side fast preclassification."""

    def __init__(self, threshold: float, fog_mips: int):
        self.impl = TOFBroker(threshold=threshold, fog_mips=fog_mips)

    def preclassify(self, step) -> Dict[str, Any]:
        klass = self.impl.classify(step)
        ec = self.impl.compute_ec(step)
        return {
            "classification": klass,
            "ec": float(ec),
            "confidence": 0.75,
            "reason": "vehicle_tof_lite",
        }


class TofFogBroker:
    """Fog-side authoritative classification and destination recommendation."""

    def __init__(self, threshold: float, fog_mips: int):
        self.impl = TOFBroker(threshold=threshold, fog_mips=fog_mips)

    def decide(self, step, vehicle_hint: Dict[str, Any], ingress_fog: str) -> Dict[str, Any]:
        klass = self.impl.classify(step)
        if klass == "boulder":
            return {
                "classification": "boulder",
                "destination": "CLOUD",
                "reason": "fog_authoritative_boulder",
                "ingress": ingress_fog,
            }
        return {
            "classification": "pebble",
            "destination": ingress_fog,
            "reason": "fog_authoritative_pebble",
            "ingress": ingress_fog,
        }
