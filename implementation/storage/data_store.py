"""Redis + PostgreSQL/Timescale storage facade with graceful fallback."""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional


class DataStore:
    """Non-breaking storage facade: Redis for live state, Postgres for history."""

    def __init__(self):
        self.enable_redis = os.getenv("ENABLE_REDIS_STATE", "false").strip().lower() in {"1", "true", "yes", "on"}
        self.enable_postgres = os.getenv("ENABLE_POSTGRES_HISTORY", "false").strip().lower() in {"1", "true", "yes", "on"}
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.pg_dsn = os.getenv("POSTGRES_DSN", "")

        self._redis = None
        self._redis_ok = False
        self._pg_ok = False
        self._lock = Lock()

        self._batch_size = max(1, int(os.getenv("STORE_BATCH_SIZE", "100")))
        self._flush_interval_s = max(0.05, float(os.getenv("STORE_FLUSH_INTERVAL_S", "1.0")))
        self._write_queue: "queue.Queue[tuple[str, Dict[str, Any]]]" = queue.Queue(maxsize=20000)
        self._stop_event = threading.Event()
        self._writer_thread: Optional[threading.Thread] = None

        self._redis_connect_timeout_s = max(0.1, float(os.getenv("REDIS_CONNECT_TIMEOUT_S", "1.0")))
        self._pg_connect_timeout_s = max(1, int(float(os.getenv("POSTGRES_CONNECT_TIMEOUT_S", "2"))))

        self._init_redis()
        self._init_postgres()
        self._start_writer_thread_if_enabled()

    def _init_redis(self) -> None:
        if not self.enable_redis:
            return
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=self._redis_connect_timeout_s,
                socket_timeout=self._redis_connect_timeout_s,
            )
            client.ping()
            self._redis = client
            self._redis_ok = True
        except KeyboardInterrupt:
            # Treat as "infra unavailable"; don't abort the whole process.
            self._redis = None
            self._redis_ok = False
        except Exception:
            self._redis = None
            self._redis_ok = False

    def _connect_pg(self):
        import psycopg2  # type: ignore

        return psycopg2.connect(self.pg_dsn, connect_timeout=self._pg_connect_timeout_s)

    def _init_postgres(self) -> None:
        if not self.enable_postgres or not self.pg_dsn:
            return
        try:
            with self._connect_pg() as conn:
                with conn.cursor() as cur:
                    timescale_available = True
                    try:
                        cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
                    except Exception:
                        timescale_available = False

                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS metrics_history (
                            id BIGSERIAL PRIMARY KEY,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            payload JSONB NOT NULL
                        );
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS task_events (
                            id BIGSERIAL PRIMARY KEY,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            payload JSONB NOT NULL
                        );
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS runtime_logs (
                            id BIGSERIAL PRIMARY KEY,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            payload JSONB NOT NULL
                        );
                        """
                    )

                    # Convert to hypertables when TimescaleDB is available.
                    if timescale_available:
                        try:
                            cur.execute(
                                "SELECT create_hypertable('metrics_history', 'created_at', if_not_exists => TRUE);"
                            )
                            cur.execute(
                                "SELECT create_hypertable('task_events', 'created_at', if_not_exists => TRUE);"
                            )
                            cur.execute(
                                "SELECT create_hypertable('runtime_logs', 'created_at', if_not_exists => TRUE);"
                            )
                        except Exception:
                            # Stay on standard Postgres tables.
                            pass

                    # Time-based indexes for historical windows.
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_metrics_created_at ON metrics_history (created_at DESC);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON task_events (created_at DESC);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_created_at ON runtime_logs (created_at DESC);")

                    # Vehicle-oriented indexed lookups from JSON payload.
                    cur.execute(
                        "CREATE INDEX IF NOT EXISTS idx_task_events_vehicle_id ON task_events ((payload->>'vehicleId'));"
                    )
                conn.commit()
            self._pg_ok = True
        except KeyboardInterrupt:
            # Treat as "infra unavailable"; don't abort the whole process.
            self._pg_ok = False
        except Exception:
            # Keep simulation running even if DB is not provisioned.
            self._pg_ok = False

    def _start_writer_thread_if_enabled(self) -> None:
        if not self._pg_ok:
            return
        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True, name="storage-batch-writer")
        self._writer_thread.start()

    def _writer_loop(self) -> None:
        pending: Dict[str, List[Dict[str, Any]]] = {
            "metrics_history": [],
            "task_events": [],
            "runtime_logs": [],
        }
        last_flush = time.time()

        while not self._stop_event.is_set():
            try:
                table_name, payload = self._write_queue.get(timeout=self._flush_interval_s)
                if table_name in pending:
                    pending[table_name].append(payload)
            except queue.Empty:
                pass

            should_flush = (time.time() - last_flush) >= self._flush_interval_s
            if not should_flush:
                for rows in pending.values():
                    if len(rows) >= self._batch_size:
                        should_flush = True
                        break

            if should_flush:
                self._flush_pending_batches(pending)
                last_flush = time.time()

        # Final flush on shutdown signal.
        self._flush_pending_batches(pending)

    def _flush_pending_batches(self, pending: Dict[str, List[Dict[str, Any]]]) -> None:
        for table_name, rows in pending.items():
            if not rows:
                continue
            self._insert_batch_pg(table_name, rows)
            rows.clear()

    def status(self) -> Dict[str, Any]:
        return {
            "redisEnabled": self.enable_redis,
            "redisConnected": self._redis_ok,
            "postgresEnabled": self.enable_postgres,
            "postgresConnected": self._pg_ok,
            "batchWriterEnabled": self._pg_ok,
            "batchSize": self._batch_size,
            "flushIntervalSeconds": self._flush_interval_s,
            "queueSize": self._write_queue.qsize() if self._pg_ok else 0,
        }

    def write_metric(self, payload: Dict[str, Any]) -> None:
        self._write_live("metrics:current", payload)
        self._push_live("metrics:history", payload, cap=2000)
        self._enqueue_pg("metrics_history", payload)

    def write_task_event(self, payload: Dict[str, Any]) -> None:
        self._push_live("tasks:recent", payload, cap=2000)
        self._enqueue_pg("task_events", payload)

    def write_runtime_log(self, payload: Dict[str, Any]) -> None:
        self._push_live("logs:recent", payload, cap=2000)
        self._enqueue_pg("runtime_logs", payload)

    def read_latest_metric(self) -> Optional[Dict[str, Any]]:
        if self._redis_ok and self._redis is not None:
            try:
                raw = self._redis.get("metrics:current")
                if raw:
                    return json.loads(raw)
            except Exception:
                pass

        rows = self._query_pg(
            "SELECT payload FROM metrics_history ORDER BY created_at DESC LIMIT 1;"
        )
        if rows:
            return rows[0]
        return None

    def read_metrics_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        limit = max(1, int(limit))
        if self._redis_ok and self._redis is not None:
            try:
                raw = self._redis.lrange("metrics:history", 0, limit - 1)
                if raw:
                    # Stored newest first; return chronological order for UI charts.
                    return [json.loads(x) for x in reversed(raw)]
            except Exception:
                pass

        rows = self._query_pg(
            "SELECT payload FROM metrics_history ORDER BY created_at DESC LIMIT %s;",
            (limit,),
        )
        return list(reversed(rows)) if rows else []

    def read_recent_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._read_recent("tasks:recent", "task_events", limit)

    def read_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._read_recent("logs:recent", "runtime_logs", limit)

    def read_metrics_window(self, hours: int, limit: int = 2000) -> List[Dict[str, Any]]:
        hours = max(1, int(hours))
        limit = max(1, int(limit))
        return self._query_pg(
            """
            SELECT payload
            FROM metrics_history
            WHERE created_at >= NOW() - make_interval(hours => %s)
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (hours, limit),
        )

    def read_task_window(self, hours: int, limit: int = 2000, vehicle_id: Optional[str] = None) -> List[Dict[str, Any]]:
        hours = max(1, int(hours))
        limit = max(1, int(limit))

        if vehicle_id:
            return self._query_pg(
                """
                SELECT payload
                FROM task_events
                WHERE created_at >= NOW() - make_interval(hours => %s)
                  AND (payload->>'vehicleId') = %s
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                (hours, vehicle_id, limit),
            )

        return self._query_pg(
            """
            SELECT payload
            FROM task_events
            WHERE created_at >= NOW() - make_interval(hours => %s)
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (hours, limit),
        )

    def read_analytics_window(self, hours: int) -> Dict[str, Any]:
        hours = max(1, int(hours))
        if not self._pg_ok:
            return {
                "hours": hours,
                "tasks": 0,
                "avgLatencyMs": 0.0,
                "avgEnergyJ": 0.0,
                "cloudExec": 0,
                "fogExec": 0,
                "localExec": 0,
                "uniqueVehicles": 0,
            }

        try:
            with self._connect_pg() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            COUNT(*)::BIGINT AS tasks,
                            COALESCE(AVG((payload->>'latencyMs')::DOUBLE PRECISION), 0.0) AS avg_latency,
                            COALESCE(AVG((payload->>'energyJ')::DOUBLE PRECISION), 0.0) AS avg_energy,
                            SUM(CASE WHEN UPPER(COALESCE(payload->>'destination', '')) = 'CLOUD' THEN 1 ELSE 0 END)::BIGINT AS cloud_exec,
                            SUM(CASE WHEN UPPER(COALESCE(payload->>'destination', '')) IN ('A','B','C','D','FOG') THEN 1 ELSE 0 END)::BIGINT AS fog_exec,
                            SUM(CASE WHEN UPPER(COALESCE(payload->>'destination', '')) = 'LOCAL' THEN 1 ELSE 0 END)::BIGINT AS local_exec,
                            COUNT(DISTINCT COALESCE(payload->>'vehicleId', ''))::BIGINT AS unique_vehicles
                        FROM task_events
                        WHERE created_at >= NOW() - make_interval(hours => %s);
                        """,
                        (hours,),
                    )
                    row = cur.fetchone()
            if not row:
                return {
                    "hours": hours,
                    "tasks": 0,
                    "avgLatencyMs": 0.0,
                    "avgEnergyJ": 0.0,
                    "cloudExec": 0,
                    "fogExec": 0,
                    "localExec": 0,
                    "uniqueVehicles": 0,
                }

            return {
                "hours": hours,
                "tasks": int(row[0] or 0),
                "avgLatencyMs": float(row[1] or 0.0),
                "avgEnergyJ": float(row[2] or 0.0),
                "cloudExec": int(row[3] or 0),
                "fogExec": int(row[4] or 0),
                "localExec": int(row[5] or 0),
                "uniqueVehicles": int(row[6] or 0),
            }
        except Exception:
            return {
                "hours": hours,
                "tasks": 0,
                "avgLatencyMs": 0.0,
                "avgEnergyJ": 0.0,
                "cloudExec": 0,
                "fogExec": 0,
                "localExec": 0,
                "uniqueVehicles": 0,
            }

    def read_vehicle_analytics_window(self, vehicle_id: str, hours: int) -> Dict[str, Any]:
        vehicle_id = (vehicle_id or "").strip()
        hours = max(1, int(hours))
        if not vehicle_id:
            return {
                "vehicleId": "",
                "hours": hours,
                "tasks": 0,
                "avgLatencyMs": 0.0,
                "avgEnergyJ": 0.0,
            }
        if not self._pg_ok:
            return {
                "vehicleId": vehicle_id,
                "hours": hours,
                "tasks": 0,
                "avgLatencyMs": 0.0,
                "avgEnergyJ": 0.0,
            }

        try:
            with self._connect_pg() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            COUNT(*)::BIGINT AS tasks,
                            COALESCE(AVG((payload->>'latencyMs')::DOUBLE PRECISION), 0.0) AS avg_latency,
                            COALESCE(AVG((payload->>'energyJ')::DOUBLE PRECISION), 0.0) AS avg_energy
                        FROM task_events
                        WHERE created_at >= NOW() - make_interval(hours => %s)
                          AND (payload->>'vehicleId') = %s;
                        """,
                        (hours, vehicle_id),
                    )
                    row = cur.fetchone()
            return {
                "vehicleId": vehicle_id,
                "hours": hours,
                "tasks": int((row[0] if row else 0) or 0),
                "avgLatencyMs": float((row[1] if row else 0.0) or 0.0),
                "avgEnergyJ": float((row[2] if row else 0.0) or 0.0),
            }
        except Exception:
            return {
                "vehicleId": vehicle_id,
                "hours": hours,
                "tasks": 0,
                "avgLatencyMs": 0.0,
                "avgEnergyJ": 0.0,
            }

    def clear_runtime(self) -> None:
        if self._redis_ok and self._redis is not None:
            try:
                self._redis.delete("metrics:current", "metrics:history", "tasks:recent", "logs:recent")
            except Exception:
                pass

    def _read_recent(self, redis_key: str, table_name: str, limit: int) -> List[Dict[str, Any]]:
        limit = max(1, int(limit))
        if self._redis_ok and self._redis is not None:
            try:
                raw = self._redis.lrange(redis_key, 0, limit - 1)
                if raw:
                    return [json.loads(x) for x in raw]
            except Exception:
                pass

        rows = self._query_pg(
            f"SELECT payload FROM {table_name} ORDER BY created_at DESC LIMIT %s;",
            (limit,),
        )
        return rows or []

    def _write_live(self, key: str, payload: Dict[str, Any]) -> None:
        if not (self._redis_ok and self._redis is not None):
            return
        try:
            self._redis.set(key, json.dumps(payload, ensure_ascii=True))
        except Exception:
            pass

    def _push_live(self, key: str, payload: Dict[str, Any], cap: int = 1000) -> None:
        if not (self._redis_ok and self._redis is not None):
            return
        try:
            with self._lock:
                self._redis.lpush(key, json.dumps(payload, ensure_ascii=True))
                self._redis.ltrim(key, 0, max(0, cap - 1))
        except Exception:
            pass

    def _enqueue_pg(self, table_name: str, payload: Dict[str, Any]) -> None:
        if not self._pg_ok:
            return
        try:
            self._write_queue.put_nowait((table_name, payload))
        except queue.Full:
            # Drop oldest by consuming one item and retry once.
            try:
                _ = self._write_queue.get_nowait()
                self._write_queue.put_nowait((table_name, payload))
            except Exception:
                pass

    def _insert_batch_pg(self, table_name: str, payloads: List[Dict[str, Any]]) -> None:
        if not self._pg_ok:
            return
        try:
            from psycopg2.extras import Json  # type: ignore
            from psycopg2.extras import execute_values  # type: ignore

            with self._connect_pg() as conn:
                with conn.cursor() as cur:
                    rows = [(datetime.utcnow(), Json(payload)) for payload in payloads]
                    execute_values(
                        cur,
                        f"INSERT INTO {table_name} (created_at, payload) VALUES %s",
                        rows,
                        template="(%s, %s)",
                    )
                conn.commit()
        except Exception:
            pass

    def _query_pg(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        if not self._pg_ok:
            return []
        try:
            with self._connect_pg() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params or ())
                    rows = cur.fetchall()
            out: List[Dict[str, Any]] = []
            for row in rows:
                payload = row[0]
                if isinstance(payload, str):
                    out.append(json.loads(payload))
                elif isinstance(payload, dict):
                    out.append(payload)
                else:
                    out.append(dict(payload))
            return out
        except Exception:
            return []


_data_store_singleton: Optional[DataStore] = None


def get_data_store() -> DataStore:
    global _data_store_singleton
    if _data_store_singleton is None:
        _data_store_singleton = DataStore()
    return _data_store_singleton
