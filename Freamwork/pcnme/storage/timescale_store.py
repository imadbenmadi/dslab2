from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from pcnme.core.config import Settings


@dataclass
class TimescaleSchema:
    metrics_table: str = "pcnme_metrics"


class TimescaleStore:
    """Optional TimescaleDB backend (requires `asyncpg` and a running DB)."""

    def __init__(self, *, settings: Settings, schema: Optional[TimescaleSchema] = None):
        self.settings = settings
        self.schema = schema or TimescaleSchema()
        self._pool = None

    async def connect(self) -> None:
        if not self.settings.TIMESCALE_DSN:
            raise RuntimeError("TIMESCALE_DSN not set")
        try:
            import asyncpg  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("asyncpg not available; install `asyncpg` to use TimescaleStore") from exc

        self._pool = await asyncpg.create_pool(dsn=self.settings.TIMESCALE_DSN, min_size=1, max_size=4)

    async def close(self) -> None:
        if self._pool is None:
            return
        await self._pool.close()
        self._pool = None

    def _require(self):
        if self._pool is None:
            raise RuntimeError("TimescaleStore not connected")
        return self._pool

    async def ensure_schema(self) -> None:
        pool = self._require()
        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.schema.metrics_table} (
                  ts TIMESTAMPTZ NOT NULL,
                  metric JSONB NOT NULL
                );
                """
            )
            # Create hypertable if Timescale extension is available
            try:
                await conn.execute(
                    f"SELECT create_hypertable('{self.schema.metrics_table}', 'ts', if_not_exists => TRUE);"
                )
            except Exception:
                # Safe fallback if extension isn't installed.
                pass

    async def insert_metric(self, *, ts_iso: str, metric: Dict[str, Any]) -> None:
        pool = self._require()
        async with pool.acquire() as conn:
            await conn.execute(
                f"INSERT INTO {self.schema.metrics_table}(ts, metric) VALUES($1::timestamptz, $2::jsonb)",
                ts_iso,
                metric,
            )
