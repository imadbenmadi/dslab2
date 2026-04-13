# Visualization Module

This module powers real-time monitoring for the React dashboard.

## Current Stack

- `api_server.py`: Flask REST API (port 5000)
- `websocket_server.py`: WebSocket live metric stream (port 8765)

No Streamlit runtime is required in the current architecture.

## Runtime Flow

1. Backend starts via `python app.py proposed` from project root.
2. Simulation generates metrics continuously.
3. Metrics are pushed to:
   - REST history/state endpoints via `api_server.py`
   - WebSocket clients via `websocket_server.py`
4. React UI (port 3000) renders live values.

## Endpoints

### REST

- `GET /api/health`
- `GET /api/status`
- `GET /api/metrics/current`
- `GET /api/metrics/history?limit=50`
- `POST /api/simulation/start`
- `POST /api/simulation/stop`
- `POST /api/simulation/reset`
- `POST /api/retrain`
- `GET /api/training-status`
- `GET /api/config`
- `GET /api/baselines`
- `GET /api/system-info`
- `GET /api/export`

### WebSocket

- `ws://127.0.0.1:8765`

Messages carry the latest system metrics snapshot used by the dashboard.

## Local Verification

From project root:

```bash
python app.py proposed
npm --prefix frontend start
```

Checks:

```bash
curl http://127.0.0.1:5000/api/health
```

Expected HTTP status: 200.

## Notes

- Root `/` on the Flask server returns a dev fallback JSON when a production React build is not present.
- WebSocket disconnect/reconnect logs are normal during backend restarts.
