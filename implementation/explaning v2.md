# Explaining V2 - Framework Runtime Logic

## 1. Goal

This project now follows a framework-oriented topology where each generated DAG task may execute locally on the car, in fog nodes, or in cloud, with AI-assisted placement/routing and contract-driven messaging.

Data-plane roles:

- Vehicle Agent service behavior: local runtime + TOF-lite preclassification.
- Fog Broker service behavior: authoritative TOF decision + queue/handoff + SDN relay.
- Cloud Orchestrator behavior: policy bundle source + analytics sink.

## 2. Main Runtime Flow

1. Vehicle telemetry and mobility are updated continuously.
2. A DAG task is generated per selected vehicle.
3. Tiny steps (low MI) execute locally on the IoT device (car).
4. Vehicle TOF-lite emits hint and Fog TOF-authoritative emits final decision.
5. Remaining steps are routed as:
    - boulder -> explicit relay path device->fog->cloud
    - pebble -> fog tier (with proactive handoff checks)
6. Pebbles to the same fog can be aggregated into a super-task.
7. Agent 2 selects SDN routing action for each remote offload unit.
8. Contract events are published to at-least-once bus with dedup.
9. Metrics, logs, and snapshots are emitted to API + WebSocket.

## 3. Agents and Training Logic

### Agent 1 (placement)

- Action space: Fog A/B/C/D or Cloud.
- Runtime policy: epsilon-greedy DQN.
- Pretraining policy: strict behavioral cloning from TOF + MMDE-NSGA-II labels only.

### Agent 2 (routing)

- Action space: primary/alt1/alt2/VIP/best-effort routing.
- Runtime policy: epsilon-greedy DQN.
- Pretraining policy: strict behavioral cloning from TOF + MMDE-NSGA-II labels only.

### SDN behavior

- Policy actions map to path profiles (primary, alt1, alt2, VIP, best effort).
- Preinstalled vs reactive flow handling is tracked.
- Packet drops and control overhead are injected into Agent2 reward.
- Relay legs are measured separately:
    - device->fog
    - fog->cloud

## 4. Where TOF + MMDE-NSGA-II Enters the Agents

1. app bootstrap generates synthetic boot tasks.
2. TOF splits each task's offloadable steps.
3. MMDE-NSGA-II optimizes pebble routing to generate Pareto/knee guidance.
4. Agent-specific pretraining pairs are extracted from optimizer output.
5. Agent pretrain methods consume only tagged pairs with source=tof-mmde-nsga2.

## 5. Full UI Pages

- Main dashboard: / (or /)
- Live full map: /map
- Agents observability: /agents
- Full logic explorer: /logic

## 6. API Endpoints for Full Observability and Control

- /api/status
- /api/metrics/current
- /api/metrics/history
- /api/map/live
- /api/agents/analytics
- /api/logic/snapshot
- /api/tasks/recent
- /api/logs/recent
- /api/evaluation/summary
- /api/control/policy
- /api/control/features
- /api/control/fleet
- /api/control/bus

## 7. Message Contracts

Contract version: v1.0.0

Event types:

- vehicle_task_submitted
- fog_decision_made
- handoff_triggered
- cloud_forwarded
- task_completed

Each event is wrapped in a versioned envelope and published through an at-least-once in-memory bus with dedup keys.

## 8. Reliability and Mobility

- Store-and-forward buffers exist at vehicle and fog layers.
- Circuit breaker protects fog->cloud relay during repeated failures.
- Proactive mobility generates fog->fog handoff events and map links.
- HTB receives mobility-stressed missed-deadline tasks.

## 9. Professional Logging

Two synchronized logs are produced:

1. results/logs/system.log
    - Human-readable rotating log with timestamp/level/message.
2. results/logs/events.jsonl
    - Structured JSON event stream for analysis/ELK/Splunk ingestion.

Examples of events:

- app_initialized
- bc_bootstrap_complete or bc_bootstrap_failed
- simulation_started/stopped/reset/completed/failed
- retraining_triggered/started/completed/failed

## 10. Metrics and Results

Key metrics tracked:

- deadline success rate
- average latency
- average energy
- tasks processed
- throughput
- handoffs and task migrations
- SDN reactive count, preinstall hits, packet drops
- relay averages for device->fog and fog->cloud
- bus publish/dedup counters and buffer sizes
- per-agent reward, penalties, updates, epsilon
- local/fog/cloud execution counts and super-task counts

## 11. Why Stop/Reset/Retrain Failed Before

In previous versions, UI control endpoints updated API state only, while simulation worker state was not fully controlled by those same actions. The runtime is now connected through callback hooks to orchestrator state and structured event logging.

## 12. Recommended Validation Checklist

1. Start backend and frontend.
2. Open /logic and verify live updates.
3. Press Start and confirm simulation_started event appears in logs.
4. Press Stop and confirm running=false in /api/logic/snapshot.
5. Press Reset and confirm counters return to zero.
6. Trigger Retrain and verify retraining lifecycle events.
7. Check system.log and events.jsonl for audit trail.
8. Check /api/control/bus for contract flow and dedup behavior.
9. Check /api/evaluation/summary for CI and trend metrics.
