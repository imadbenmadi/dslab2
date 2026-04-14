from __future__ import annotations

from dataclasses import dataclass

from pcnme.core.enums import TaskClass
from pcnme.core.task import DAGStep


@dataclass(frozen=True)
class TOFDecision:
    classification: TaskClass
    ec_seconds: float


class TOFBroker:
    """Time-Of-Flight broker: EC-based boulder/pebble classification."""

    def __init__(self, *, fog_mips: int, threshold_s: float):
        self.fog_mips = int(fog_mips)
        self.threshold_s = float(threshold_s)

    def compute_ec(self, step_mi: float) -> float:
        return float(step_mi) / float(self.fog_mips)

    def classify(self, step_mi: float) -> TaskClass:
        # Spec: boulder if EC >= threshold
        ec = self.compute_ec(step_mi)
        return TaskClass.BOULDER if ec >= self.threshold_s else TaskClass.PEBBLE

    def decide(self, step: DAGStep) -> TOFDecision:
        ec = self.compute_ec(step.MI)
        klass = TaskClass.BOULDER if ec >= self.threshold_s else TaskClass.PEBBLE
        return TOFDecision(classification=klass, ec_seconds=float(ec))
