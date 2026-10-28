from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from pcnme.core.enums import OffloadTarget


@dataclass
class DAGStep:
    id: int
    name: str
    MI: float
    in_KB: float
    out_KB: float
    deadline_ms: Optional[float] = None
    runs_on: OffloadTarget = OffloadTarget.FOG


@dataclass
class DAGTask:
    id: str
    vehicle_id: str
    sim_time_s: float
    steps: Dict[int, DAGStep] = field(default_factory=dict)


@dataclass
class TaskBatch:
    tasks: list[DAGTask]
