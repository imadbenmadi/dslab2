# Codebase Structure (Cleaned)

This map clarifies each top-level folder and why it exists.

## Runtime Layers

- `app.py`
    - Unified runtime entrypoint for simulation + API + WebSocket startup.
    - Keeps orchestration in one process for local thesis demos.

- `simulation/`
    - Simulation engine components.
    - Main active module: `runner.py`.

- `visualization/`
    - Delivery layer for frontend consumption.
    - `api_server.py` serves REST endpoints.
    - `websocket_server.py` streams live metrics.

- `framework/`
    - Cross-cutting runtime building blocks shared by modules.
    - Contracts, messaging reliability, policy sync, identity/security.

- `app_runtime/`
    - Runtime glue/adapters for `app.py`.
    - Example: route registration extracted from `app.py`.

## Core Domain Modules

- `agents/`: DQN Agent 1 + Agent 2 logic.
- `broker/`: TOF broker, task splitting roles.
- `optimizer/`: NSGA-II + MMDE optimizer.
- `mobility/`: handoff and trajectory logic.
- `sdn/`: SDN controller and routing control logic.
- `environment/`: task, vehicle, fog, cloud domain entities.

## Infrastructure Modules

- `infrastructure/`
    - Transport/security/helper integrations (NATS, PKI, model signing, cert management).

- `storage/`
    - Redis live state + PostgreSQL/Timescale historical storage facade.
    - Includes background batch writer and indexed history queries.

## Frontend

- `frontend/`
    - React dashboard and observability UI.

## Cleaned Up Items

The following were removed as unused/dead code to reduce confusion:

- `baselines/baseline1.py`
- `baselines/baseline2.py`
- `baselines/baseline3.py`
- `visualization/dashboard.py`
- `visualization/examples.py`
- `simulation/env.py`

## Naming Notes

- `framework` means shared platform primitives, not business logic.
- `app_runtime` means entrypoint wiring extracted from `app.py`.
- `simulation` means workload execution model.
- `visualization` means REST/WebSocket delivery and monitoring endpoints.

If desired, a future rename can map:

- `framework` -> `platform_core`
- `app_runtime` -> `bootstrap`
- `visualization` -> `interfaces`
- `simulation` -> `engine`

That rename is possible with import migration, but was not applied yet to avoid runtime breakage.
