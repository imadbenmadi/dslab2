from __future__ import annotations

from dataclasses import dataclass

from pcnme.core.enums import HandoffMode


@dataclass(frozen=True)
class HandoffDecision:
    mode: HandoffMode
    reason: str


class HandoffManager:
    def select_mode(self, *, t_exit_s: float, t_exec_s: float) -> HandoffDecision:
        if t_exec_s < t_exit_s:
            return HandoffDecision(mode=HandoffMode.DIRECT, reason="exec_before_exit")
        return HandoffDecision(mode=HandoffMode.PROACTIVE, reason="exit_before_exec")
