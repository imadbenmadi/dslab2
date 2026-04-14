from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from pcnme.agents.dqn import DQNAgent, DQNConfig
from pcnme.agents.torch_support import require_torch


@dataclass(frozen=True)
class BCDataset:
    X: np.ndarray  # (n, state_dim)
    y: np.ndarray  # (n,)


@dataclass(frozen=True)
class BCTrainResult:
    epochs: int
    final_loss: float


def train_behavior_cloning(
    *,
    dataset: BCDataset,
    cfg: DQNConfig,
    epochs: int,
    seed: int,
    out_path: Optional[Path] = None,
) -> Tuple[DQNAgent, BCTrainResult]:
    ts = require_torch()
    torch = ts.torch
    nn = ts.nn
    optim = ts.optim

    rng = np.random.default_rng(int(seed))
    X = np.asarray(dataset.X, dtype=np.float32)
    y = np.asarray(dataset.y, dtype=np.int64)

    agent = DQNAgent(cfg=cfg, seed=seed)
    model = agent.q
    model.train()

    opt = optim.Adam(model.parameters(), lr=float(cfg.lr))
    loss_fn = nn.CrossEntropyLoss()

    idxs = np.arange(len(X))
    final_loss = 0.0
    for _ in range(int(epochs)):
        rng.shuffle(idxs)
        for start in range(0, len(idxs), int(cfg.batch_size)):
            batch = idxs[start : start + int(cfg.batch_size)]
            xb = torch.tensor(X[batch], dtype=torch.float32, device=agent.device)
            yb = torch.tensor(y[batch], dtype=torch.int64, device=agent.device)

            logits = model(xb)
            loss = loss_fn(logits, yb)
            opt.zero_grad()
            loss.backward()
            opt.step()
            final_loss = float(loss.item())

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        agent.save(str(out_path))

    return agent, BCTrainResult(epochs=int(epochs), final_loss=float(final_loss))
