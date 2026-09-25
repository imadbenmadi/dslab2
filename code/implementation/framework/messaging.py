from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Any, Optional, List


@dataclass
class MessageRecord:
    id: str
    topic: str
    payload: Dict[str, Any]
    retries: int = 0


class AtLeastOnceBus:
    """In-memory at-least-once bus with dedup support by message id."""

    def __init__(self, max_messages: int = 5000):
        self._topics: Dict[str, Deque[MessageRecord]] = {}
        self._seen_ids: Dict[str, bool] = {}
        self._max_messages = max_messages
        self._published = 0
        self._dedup_dropped = 0

    def publish(self, topic: str, message_id: str, payload: Dict[str, Any]) -> bool:
        if message_id in self._seen_ids:
            self._dedup_dropped += 1
            return False

        self._seen_ids[message_id] = True
        q = self._topics.setdefault(topic, deque(maxlen=self._max_messages))
        q.append(MessageRecord(id=message_id, topic=topic, payload=payload))
        self._published += 1
        return True

    def consume(self, topic: str) -> Optional[MessageRecord]:
        q = self._topics.get(topic)
        if not q:
            return None
        if len(q) == 0:
            return None
        return q.popleft()

    def peek_topic(self, topic: str, limit: int = 20) -> List[Dict[str, Any]]:
        q = self._topics.get(topic, deque())
        return [r.payload for r in list(q)[-limit:]]

    def status(self) -> Dict[str, Any]:
        return {
            "published": self._published,
            "dedupDropped": self._dedup_dropped,
            "topics": {k: len(v) for k, v in self._topics.items()},
        }


class StoreForwardBuffer:
    """Generic store-and-forward queue for disrupted links."""

    def __init__(self, capacity: int = 5000):
        self.capacity = int(max(1, capacity))
        self.buffer: Deque[Dict[str, Any]] = deque(maxlen=self.capacity)

    def push(self, item: Dict[str, Any]):
        self.buffer.append(item)

    def pop(self) -> Optional[Dict[str, Any]]:
        if not self.buffer:
            return None
        return self.buffer.popleft()

    def drain(self, limit: int = 100) -> List[Dict[str, Any]]:
        items = []
        while self.buffer and len(items) < limit:
            items.append(self.buffer.popleft())
        return items

    def size(self) -> int:
        return len(self.buffer)


class CircuitBreaker:
    """Simple circuit breaker for unstable links/services."""

    def __init__(self, fail_threshold: int = 10, recovery_after: int = 30):
        self.fail_threshold = max(1, int(fail_threshold))
        self.recovery_after = max(1, int(recovery_after))
        self.failures = 0
        self.open_until = -1

    def is_open(self, current_tick: int) -> bool:
        return self.open_until >= current_tick

    def on_success(self):
        self.failures = max(0, self.failures - 1)

    def on_failure(self, current_tick: int):
        self.failures += 1
        if self.failures >= self.fail_threshold:
            self.open_until = current_tick + self.recovery_after
            self.failures = 0
