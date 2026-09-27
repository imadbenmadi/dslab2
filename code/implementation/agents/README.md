# Agents Module - DQN Learning Systems

## Purpose

This module implements Deep Q-Networks (DQN) for two critical decision-making tasks:

### Agent1: Task Placement Optimization

- **Decides WHERE each task goes:** Local device, Fog node, or Cloud
- **Observes:** Device load, task complexity, fog queue depth, network conditions
- **Output:** Best infrastructure placement
- **Reward:** Minimize latency + energy, maximize deadline success

### Agent2: SDN Network Routing

- **Decides HOW packets route through network:** Which path, which priority
- **Observes:** Network topology, link congestion, available bandwidth
- **Output:** Best routing decision
- **Reward:** Minimize transmission latency and congestion

## Why We Used It

The system needs **online adaptive decision-making** rather than static rules because:

- **Network conditions change** (congestion, mobility, failures)
- **Task properties vary** (size, deadline, priority)
- **Infrastructure state fluctuates** (load balancing, resource availability)

DQN agents learn from experience through trial-and-error (with guided pre-training) and can adapt to runtime conditions the optimization phase never saw.

## How We Used It in the Full System

### Training Pipeline:

```
1. NSGA-II generates Pareto-optimal solutions offline
   ↓
2. Behavioral Cloning: Train agents on NSGA-II demonstrations
   ↓
3. Online Learning: DQN continues learning during simulation
   ↓
4. Real-Time Decisions: Agents make placement/routing calls
   ↓
5. Rewards: Metrics feedback improves agent knowledge
```

### Integration:

- **Pre-training:** `main.py` trains agents using behavioral cloning
- **Execution:** `simulation/runner.py` calls agents for every task/packet
- **Evaluation:** Dashboard shows agent decisions in real-time

## Files

- **agent1.py** (150 lines) - Task placement agent
- **agent2.py** (150 lines) - SDN routing agent
- **dqn.py** (200 lines) - Shared neural network architecture
    - 2-layer neural network (256 → 128 neurons)
    - Experience replay buffer (10,000 capacity)
    - Target network for stability
    - Adam optimizer (learning rate: 0.001)

## Performance

| Metric           | With Agents | Without Agents    |
| ---------------- | ----------- | ----------------- |
| Deadline Success | >85%        | 81.2% (baseline3) |
| Avg Latency      | <80ms       | 163ms             |
| Avg Energy       | <0.12J      | 0.157J            |

Agents provide **4-5% improvement** over best static baseline through adaptive decisions.

## Key Innovation

**Hybrid approach:** Combine NSGA-II's global optimization with DQN's online adaptation. This gives agents a "good starting point" (behavioral cloning) before they learn further from environment feedback.
