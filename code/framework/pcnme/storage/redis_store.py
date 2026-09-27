from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pcnme.core.config import Settings


@dataclass
class RedisKeys:
    latest_state: str = "pcnme:state:latest"
    metrics_stream: str = "pcnme:metrics:stream"
    pubsub_channel: str = "pcnme:events"


class RedisStore:
    def __init__(self, *, settings: Settings, keys: Optional[RedisKeys] = None):
        self.settings = settings
        self.keys = keys or RedisKeys()
        self._redis = None

    async def connect(self) -> None:
        try:
            import redis.asyncio as redis  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Redis client not available. Install dependency `redis` and ensure Redis is reachable."
            ) from exc

        self._redis = redis.from_url(self.settings.REDIS_URL, decode_responses=True)
        await self._redis.ping()

    async def close(self) -> None:
        if self._redis is None:
            return
        await self._redis.close()
        self._redis = None

    def _require(self):
        if self._redis is None:
            raise RuntimeError("RedisStore not connected")
        return self._redis

    @property
    def client(self):
        return self._require()

    async def set_latest_state(self, state: Dict[str, Any]) -> None:
        r = self._require()
        payload = json.dumps({"ts": _utc_now_iso(), "state": state})
        await r.set(self.keys.latest_state, payload)
        await r.publish(self.keys.pubsub_channel, payload)

    async def append_metric(self, metric: Dict[str, Any]) -> None:
        r = self._require()
        payload = json.dumps({"ts": _utc_now_iso(), **metric})
        # Use Redis Streams for ordered metrics storage
        await r.xadd(self.keys.metrics_stream, {"json": payload}, maxlen=20000, approximate=True)

    async def get_latest_state(self) -> Optional[Dict[str, Any]]:
        r = self._require()
        raw = await r.get(self.keys.latest_state)
        if not raw:
            return None
        data = json.loads(raw)
        return data


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

