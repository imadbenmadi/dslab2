from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from pcnme.core.config import Settings
from pcnme.core.topology import Topology
from pcnme.simulation.engine import SimulationEngine
from pcnme.storage.redis_store import RedisStore


def create_app(*, settings: Settings, topology: Topology) -> FastAPI:
    store = RedisStore(settings=settings)
    engine = SimulationEngine(settings=settings, topology=topology, store=store)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await store.connect()
        yield
        await engine.stop()
        await store.close()

    app = FastAPI(title="PCNME Runtime", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "sim": engine.status().__dict__}

    @app.get("/api/state")
    async def state():
        latest = await store.get_latest_state()
        if latest:
            return latest
        return {"ts": datetime.now(timezone.utc).isoformat(), "state": engine.snapshot().to_dict()}

    @app.get("/api/metrics/summary")
    async def metrics_summary():
        return engine.snapshot().metrics.__dict__

    @app.post("/api/sim/start")
    async def sim_start():
        await engine.start()
        return engine.status().__dict__

    @app.post("/api/sim/stop")
    async def sim_stop():
        await engine.stop()
        return engine.status().__dict__

    @app.websocket(settings.WS_PATH)
    async def ws_stream(ws: WebSocket):
        await ws.accept()
        r = store.client
        pubsub = r.pubsub()
        await pubsub.subscribe(store.keys.pubsub_channel)
        try:
            # send one snapshot immediately
            latest = await store.get_latest_state()
            await ws.send_json(
                latest or {"ts": datetime.now(timezone.utc).isoformat(), "state": engine.snapshot().to_dict()}
            )

            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("data"):
                    # data is the JSON payload written by RedisStore
                    await ws.send_text(str(msg["data"]))
                await asyncio.sleep(0.05)
        except WebSocketDisconnect:
            pass
        finally:
            try:
                await pubsub.unsubscribe(store.keys.pubsub_channel)
                await pubsub.close()
            except Exception:
                pass

    return app
