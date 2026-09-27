from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pcnme.core.enums import TaskClass
from pcnme.core.task import DAGStep


@dataclass(frozen=True)
class AggregationDecision:
    aggregated: bool
    task_class: TaskClass
    super_step: Optional[DAGStep]
    original_step_ids: List[int]
    reason: str


class Aggregator:
    """Avalanche prevention by bundling pebble steps into a super-task."""

    def __init__(self, *, q_max: int):
        self.q_max = int(q_max)

    def should_aggregate(self, queue_depth: int) -> bool:
        return int(queue_depth) > self.q_max

    def aggregate(self, steps: List[DAGStep], *, super_step_id: int = 999) -> DAGStep:
        total_mi = sum(float(s.MI) for s in steps)
        total_in_kb = sum(float(s.in_KB) for s in steps)
        total_out_kb = sum(float(s.out_KB) for s in steps)
        return DAGStep(
            id=int(super_step_id),
            name="SuperTask",
            MI=float(total_mi),
            in_KB=float(total_in_kb),
            out_KB=float(total_out_kb),
            deadline_ms=min([s.deadline_ms for s in steps if s.deadline_ms is not None], default=None),
        )

    def maybe_aggregate(self, *, queue_depth: int, pending_steps: List[DAGStep]) -> AggregationDecision:
        if not pending_steps:
            return AggregationDecision(
                aggregated=False,
                task_class=TaskClass.PEBBLE,
                super_step=None,
                original_step_ids=[],
                reason="no_pending_steps",
            )

        if not self.should_aggregate(queue_depth):
            return AggregationDecision(
                aggregated=False,
                task_class=TaskClass.PEBBLE,
                super_step=None,
                original_step_ids=[s.id for s in pending_steps],
                reason="queue_below_threshold",
            )

        super_step = self.aggregate(pending_steps)
        return AggregationDecision(
            aggregated=True,
            task_class=TaskClass.SUPER_PEBBLE,
            super_step=super_step,
            original_step_ids=[s.id for s in pending_steps],
            reason="queue_above_q_max",
        )
