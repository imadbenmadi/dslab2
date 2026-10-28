from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class NTBItem:
    task_id: str
    payload: Dict[str, Any]


class NTBBuffer:
    """Normal Task Buffer."""

    def __init__(self, *, capacity: int):
        self.capacity = int(capacity)
        self._items: List[NTBItem] = []

    def push(self, item: NTBItem) -> None:
        if len(self._items) >= self.capacity:
            self._items.pop(0)
        self._items.append(item)

    def pop(self) -> NTBItem | None:
        if not self._items:
            return None
        return self._items.pop(0)

    def __len__(self) -> int:
        return len(self._items)


class HTBBuffer:
    """Handoff Task Buffer: holds results while a vehicle is disconnected."""

    def __init__(self):
        self._results_by_vehicle: Dict[str, List[Dict[str, Any]]] = {}

    def store_result(self, *, vehicle_id: str, result: Dict[str, Any]) -> None:
        self._results_by_vehicle.setdefault(vehicle_id, []).append(result)

    def deliver_on_reconnect(self, *, vehicle_id: str) -> List[Dict[str, Any]]:
        return self._results_by_vehicle.pop(vehicle_id, [])
