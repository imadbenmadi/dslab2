from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from pcnme.agents.bc import BCDataset, train_behavior_cloning
from pcnme.agents.dqn import DQNConfig
from pcnme.agents.features import build_agent2_state
from pcnme.core.config import Settings
from pcnme.sdn.controller import SDNController


def expected_route_score(
    *,
    controller: SDNController,
    action: int,
    queue_pressure: float,
    payload_kb: float,
    destination_is_cloud: bool,
    preinstall_hit: bool,
    packet_drop_penalty: float,
) -> float:
    profile = controller.path_profiles.get(int(action), controller.path_profiles[0])
    q = float(max(0.0, min(1.0, queue_pressure)))

    hops = int(profile["hops"]) + (1 if destination_is_cloud else 0)
    propagation_ms = float(profile["base_ms"] + 0.5 * float(profile["jitter_ms"]))
    queue_ms = (3.0 + 10.0 * q) * (0.7 if int(action) == 3 else 1.0)
    size_ms = min(max(float(payload_kb), 1.0) / 180.0, 8.0)
    hop_ms = hops * 0.9
    path_delay_ms = propagation_ms + queue_ms + size_ms + hop_ms

    if preinstall_hit:
        ctrl_ms = float(controller.settings.SDN_PREINSTALL_MS)
    else:
        ctrl_ms = float(controller.settings.SDN_REACTIVE_MS) * (1.0 + 0.6 * q)

    drop_prob = float(profile["loss"] * (1.0 + 0.8 * q))
    expected_drop_cost = drop_prob * float(packet_drop_penalty)
    return float(path_delay_ms + ctrl_ms + expected_drop_cost)


def label_routing_action(
    *,
    settings: Settings,
    queue_pressure: float,
    payload_kb: float,
    destination_is_cloud: bool,
    preinstall_hit: bool,
) -> int:
    controller = SDNController(settings=settings)
    scores = [
        expected_route_score(
            controller=controller,
            action=a,
            queue_pressure=queue_pressure,
            payload_kb=payload_kb,
            destination_is_cloud=destination_is_cloud,
            preinstall_hit=preinstall_hit,
            packet_drop_penalty=float(settings.AGENT2_PACKET_DROP_PENALTY),
        )
        for a in range(int(settings.AGENT2_ACTION_DIM))
    ]
    return int(np.argmin(np.asarray(scores, dtype=float)))


@dataclass(frozen=True)
class Agent2BCBuildResult:
    dataset: BCDataset
    samples: int


def build_agent2_bc_dataset(
    *,
    settings: Settings,
    samples: int,
    seed: int,
) -> Agent2BCBuildResult:
    rng = np.random.default_rng(int(seed))

    X_list: List[np.ndarray] = []
    y_list: List[int] = []

    for _ in range(int(samples)):
        q = float(rng.uniform(0.0, 1.0))
        payload_kb = float(rng.uniform(1.0, 600.0))
        destination_is_cloud = bool(rng.random() < 0.4)
        preinstall_hit = bool(rng.random() < 0.5)

        action = label_routing_action(
            settings=settings,
            queue_pressure=q,
            payload_kb=payload_kb,
            destination_is_cloud=destination_is_cloud,
            preinstall_hit=preinstall_hit,
        )
        state = build_agent2_state(
            queue_pressure=q,
            payload_kb=payload_kb,
            destination_is_cloud=destination_is_cloud,
            preinstall_hit=preinstall_hit,
            settings=settings,
        )
        X_list.append(state)
        y_list.append(int(action))

    X = np.stack(X_list).astype(np.float32)
    y = np.asarray(y_list, dtype=np.int64)
    return Agent2BCBuildResult(dataset=BCDataset(X=X, y=y), samples=int(len(y)))


def train_agent2_bc(
    *,
    settings: Settings,
    samples: int,
    epochs: int,
    seed: int,
    out_path: Path,
) -> Tuple[object, object, Agent2BCBuildResult]:
    build = build_agent2_bc_dataset(settings=settings, samples=samples, seed=seed)
    cfg = DQNConfig(
        state_dim=int(settings.AGENT2_STATE_DIM),
        action_dim=int(settings.AGENT2_ACTION_DIM),
        hidden_layers=list(settings.AGENT2_HIDDEN),
        lr=float(settings.AGENT2_LR),
        gamma=float(settings.AGENT2_GAMMA),
        batch_size=int(settings.AGENT2_BATCH_SIZE),
        buffer_size=int(settings.AGENT2_BUFFER_SIZE),
        target_update=int(settings.AGENT2_TARGET_UPDATE),
    )
    agent, result = train_behavior_cloning(dataset=build.dataset, cfg=cfg, epochs=epochs, seed=seed, out_path=out_path)
    return agent, result, build
