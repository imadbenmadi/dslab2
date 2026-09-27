# Smart City Vehicular Task Offloading System

Production-grade smart city simulation with three distributed microservices. Features real-time React dashboard, TOF+MMDE-NSGA-II optimization, and mTLS-secured inter-service communication.

## Architecture

**New:** Distributed microservices with NATS messaging and mTLS

```text
┌────────────────────┐         ┌──────────────────┐         ┌───────────────────┐
│ Vehicle Service    │         │  Fog Service     │         │ Cloud Service     │
│ • Agent1 (place)   │◄────────┤ • Agent2 (route) │◄────────┤ • Flask API       │
│ • TOF lite         │  NATS   │ • SDN Controller │  NATS   │ • WebSocket       │
│ • 50 Vehicles      │  mTLS   │ • TOF broker     │  mTLS   │ • Analytics       │
└────────────────────┘         └──────────────────┘         └───────────────────┘
```

See [DISTRIBUTED_ARCHITECTURE.md](DISTRIBUTED_ARCHITECTURE.md) for detailed docs.

## Quick Start (Recommended: Distributed Services)

### 1. Install dependencies

```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### 1.1 Optional: configure via environment variables

```bash
# Linux/macOS
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

Update `.env` values as needed. The app loads `.env` automatically via `config.py`.

### 1.2 Optional: start Redis + TimescaleDB (one command)

```powershell
./scripts/start_infra.ps1
```

Equivalent Docker command:

```bash
docker compose up -d redis timescaledb
```

### 2. Start NATS broker

```bash
# Using Docker (recommended)
docker run -d --name nats -p 4222:4222 nats:latest

# Or install locally: https://docs.nats.io/running-a-nats-server/installation
```

### 3. Start all three services

```bash
# This generates mTLS certs and starts vehicle, fog, and cloud services
python -m services.orchestrator
```

### 4. Start frontend (separate terminal)

```bash
cd frontend
npm start
```

### 5. Open dashboard

- Dashboard: http://localhost:3000
- Thesis Architecture: http://localhost:3000/thesis
- API health: http://127.0.0.1:5000/api/health
- Cloud analytics: http://127.0.0.1:5000/api/cloud/analytics
- WebSocket (used by React): ws://127.0.0.1:8765

---

## Quick Start (Legacy: Monolithic)

For backward compatibility, the old single-process version is still available:

```bash
python app.py proposed
```

**Note:** The monolithic version will be deprecated in future releases. Use distributed services for production.

---

## Architecture Details

### Services

- **vehicle-service** – Vehicles (N=50), Agent1 DQN, TOF-lite broker
- **fog-service** – Fog nodes (N=4), Agent2 DQN, SDN controller, TOF authoritative
- **cloud-service** – Flask API, WebSocket, analytics, control plane

### Communication

- **Message Broker:** NATS (native TLS)
- **Security:** mTLS with auto-generated certificates
- **Contracts:** Typed event dataclasses with schema validation
- **Dedup:** UUID-based message tracking per contract event

### Data Flow

1. **Vehicle submission:** Vehicle generates task → Publish `VehicleTaskSubmitted`
2. **Fog decision:** Fog classifies → Publish `FogDecisionMade`
3. **Analytics:** Cloud aggregates all events → REST API & WebSocket
4. **Control plane:** Policy sync & feature flags via NATS

## Project Structure

```text
implementation/
├── app.py
├── config.py
├── requirements.txt
├── explanation.md
├── agents/
├── baselines/
├── broker/
├── environment/
├── mobility/
├── optimizer/
├── results/
├── sdn/
├── simulation/
├── visualization/
└── frontend/
```

## API Endpoints

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
- `GET /api/evaluation/summary`
- `GET|POST /api/control/policy`
- `POST /api/control/features`
- `POST /api/control/fleet`
- `GET /api/control/bus`
- `GET /api/analytics/window?window=1h|24h`
- `GET /api/analytics/vehicle/<vehicle_id>?window=24h&limit=200`

## Data Infrastructure (Redis + Timescale/PostgreSQL)

- Live state feed: Redis
- Historical storage: TimescaleDB/PostgreSQL
- Write mode: background batch writer for lower DB overhead under load

Startup:

```powershell
./scripts/start_infra.ps1
```

or

```bash
docker compose up -d redis timescaledb
```

## Common Issues

### Dashboard opens but Start fails

This was fixed by preventing click event objects from being serialized in `startSimulation`.

### API works but dashboard not loading

Make sure React is running:

```bash
npm --prefix frontend start
```

### WebSocket reconnect logs

Occasional reconnect logs are expected during backend restart.

## Documentation

- [explanation.md](explanation.md)
- [THESIS_ARCHITECTURE_PROPOSAL_V2.md](THESIS_ARCHITECTURE_PROPOSAL_V2.md)
- [CODEBASE_STRUCTURE.md](CODEBASE_STRUCTURE.md)
- [explaning v2.md](explaning%20v2.md)
- [frontend/README.md](frontend/README.md)
- [visualization/README.md](visualization/README.md)
- Module READMEs in each folder

## Status

- Backend: working
- API: working
- WebSocket: working
- Frontend: working

## bootstrap

ENABLE_BOOTSTRAP_PRETRAIN: turn this startup pretraining on/off.
BOOTSTRAP_TASKS: how many synthetic bootstrap DAG tasks to generate.
BOOTSTRAP_NSGA_POP_SIZE: NSGA population size used only during bootstrap (smaller = faster, less quality).
BOOTSTRAP_NSGA_GENS: NSGA generations during bootstrap (more = better search, slower startup).
BOOTSTRAP_MAX_SECONDS: hard time budget; bootstrap stops when this startup time cap is reached.
In short: it is a controlled startup pretraining step with quality/speed guards, not full training.
It prevents long blocking at launch while still giving agents a better initial policy.
