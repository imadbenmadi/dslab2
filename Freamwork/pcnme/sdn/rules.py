from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FlowRule:
    flow_id: str
    src: str
    dst: str
    priority: int
    actions: List[str]
    installed_at_sim_s: float
    hit_count: int = 0
    ttl_s: Optional[float] = None


class RuleCache:
    def __init__(self):
        self._rules: Dict[str, FlowRule] = {}

    def key(self, src: str, dst: str, flow_id: str) -> str:
        return f"{src}->{dst}:{flow_id}"

    def upsert(self, rule: FlowRule) -> None:
        self._rules[self.key(rule.src, rule.dst, rule.flow_id)] = rule

    def has(self, *, src: str, dst: str) -> bool:
        return any(r.src == src and r.dst == dst for r in self._rules.values())

    def active_rules(self) -> List[FlowRule]:
        return list(self._rules.values())
