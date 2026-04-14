from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from pcnme.agents.bc import BCDataset, train_behavior_cloning
from pcnme.agents.dqn import DQNConfig
from pcnme.agents.features import build_agent1_state
from pcnme.core.config import Settings
from pcnme.core.topology import Topology
from pcnme.datasets.synthetic import SyntheticGenerator
from pcnme.optimizer.nsga2_mmde import run_nsga2_mmde
from pcnme.optimizer.pareto import select_knee_point
from pcnme.optimizer.problem import TaskOffloadingProblem


@dataclass(frozen=True)
class Agent1BCBuildResult:
    dataset: BCDataset
    samples: int


def build_agent1_bc_dataset(
    *,
    settings: Settings,
    topology: Topology,
    batches: int,
    batch_size: int,
    seed: Optional[int] = None,
) -> Agent1BCBuildResult:
    rng = np.random.default_rng(settings.RANDOM_SEED if seed is None else int(seed))
    gen = SyntheticGenerator(settings=settings, topology=topology, rng=rng)

    X_list: List[np.ndarray] = []
    y_list: List[int] = []

    for batch_idx in range(int(batches)):
        units = gen.generate_pebble_units(batch_size=int(batch_size), batch_index=batch_idx)
        fog_loads: Dict[str, float] = gen.sample_fog_loads()

        problem = TaskOffloadingProblem(settings=settings, topology=topology, units=units, fog_loads=fog_loads)
        res = run_nsga2_mmde(
            problem=problem,
            pop_size=int(settings.NSGA_POP_SIZE),
            n_gens=int(settings.NSGA_GENS),
            F=float(settings.MMDE_F),
            CR=float(settings.MMDE_CR),
            seed=int(rng.integers(0, 2**31 - 1)),
            verbose=False,
        )
        knee = select_knee_point(np.asarray(res.F, dtype=float))
        actions = np.asarray(res.X[knee.index], dtype=int)

        for unit, action in zip(units, actions):
            state = build_agent1_state(unit=unit, settings=settings, topology=topology, fog_loads=fog_loads)
            X_list.append(state)
            y_list.append(int(action))

    X = np.stack(X_list).astype(np.float32)
    y = np.asarray(y_list, dtype=np.int64)
    return Agent1BCBuildResult(dataset=BCDataset(X=X, y=y), samples=int(len(y)))


def train_agent1_bc(
    *,
    settings: Settings,
    topology: Topology,
    batches: int,
    batch_size: int,
    epochs: int,
    seed: int,
    out_path: Path,
):
    build = build_agent1_bc_dataset(settings=settings, topology=topology, batches=batches, batch_size=batch_size, seed=seed)
    cfg = DQNConfig(
        state_dim=int(settings.AGENT1_STATE_DIM),
        action_dim=int(settings.AGENT1_ACTION_DIM),
        hidden_layers=list(settings.AGENT1_HIDDEN),
        lr=float(settings.AGENT1_LR),
        gamma=float(settings.AGENT1_GAMMA),
        batch_size=int(settings.AGENT1_BATCH_SIZE),
        buffer_size=int(settings.AGENT1_BUFFER_SIZE),
        target_update=int(settings.AGENT1_TARGET_UPDATE),
    )
    agent, result = train_behavior_cloning(dataset=build.dataset, cfg=cfg, epochs=epochs, seed=seed, out_path=out_path)
    return agent, result, build
