from __future__ import annotations

from dataclasses import dataclass
from typing import Deque, List, Optional, Tuple

import numpy as np

from pcnme.agents.torch_support import require_torch


@dataclass(frozen=True)
class DQNConfig:
    state_dim: int
    action_dim: int
    hidden_layers: List[int]
    lr: float
    gamma: float
    batch_size: int
    buffer_size: int
    target_update: int


class ReplayBuffer:
    def __init__(self, *, capacity: int, state_dim: int):
        from collections import deque

        self.capacity = int(capacity)
        self.state_dim = int(state_dim)
        self._buf: Deque[Tuple[np.ndarray, int, float, np.ndarray, bool]] = deque(maxlen=self.capacity)

    def push(self, s: np.ndarray, a: int, r: float, s2: np.ndarray, done: bool) -> None:
        self._buf.append((np.asarray(s, dtype=np.float32), int(a), float(r), np.asarray(s2, dtype=np.float32), bool(done)))

    def __len__(self) -> int:
        return len(self._buf)

    def sample(self, batch_size: int, *, rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        idxs = rng.choice(len(self._buf), size=int(batch_size), replace=False)
        s, a, r, s2, d = zip(*[self._buf[int(i)] for i in idxs])
        return (
            np.stack(s).astype(np.float32),
            np.asarray(a, dtype=np.int64),
            np.asarray(r, dtype=np.float32),
            np.stack(s2).astype(np.float32),
            np.asarray(d, dtype=np.float32),
        )


def _build_mlp(nn, in_dim: int, hidden: List[int], out_dim: int):
    layers = []
    last = int(in_dim)
    for h in hidden:
        layers.append(nn.Linear(last, int(h)))
        layers.append(nn.ReLU())
        last = int(h)
    layers.append(nn.Linear(last, int(out_dim)))
    return nn.Sequential(*layers)


class DQNAgent:
    def __init__(self, *, cfg: DQNConfig, seed: int = 0, device: Optional[str] = None):
        ts = require_torch()
        self.torch = ts.torch
        self.nn = ts.nn
        self.optim = ts.optim

        self.cfg = cfg
        self.rng = np.random.default_rng(int(seed))
        self.device = self.torch.device(device or ("cuda" if self.torch.cuda.is_available() else "cpu"))

        self.q = _build_mlp(self.nn, cfg.state_dim, cfg.hidden_layers, cfg.action_dim).to(self.device)
        self.q_target = _build_mlp(self.nn, cfg.state_dim, cfg.hidden_layers, cfg.action_dim).to(self.device)
        self.q_target.load_state_dict(self.q.state_dict())
        self.q_target.eval()

        self.optimizer = self.optim.Adam(self.q.parameters(), lr=float(cfg.lr))
        self.steps = 0
        self.buffer = ReplayBuffer(capacity=cfg.buffer_size, state_dim=cfg.state_dim)

    def act(self, state: np.ndarray, *, epsilon: float) -> int:
        if float(self.rng.random()) < float(epsilon):
            return int(self.rng.integers(0, self.cfg.action_dim))
        with self.torch.no_grad():
            s = self.torch.tensor(state, dtype=self.torch.float32, device=self.device).unsqueeze(0)
            q = self.q(s)
            return int(self.torch.argmax(q, dim=1).item())

    def train_step(self) -> Optional[float]:
        if len(self.buffer) < self.cfg.batch_size:
            return None

        s, a, r, s2, d = self.buffer.sample(self.cfg.batch_size, rng=self.rng)

        s_t = self.torch.tensor(s, dtype=self.torch.float32, device=self.device)
        a_t = self.torch.tensor(a, dtype=self.torch.int64, device=self.device)
        r_t = self.torch.tensor(r, dtype=self.torch.float32, device=self.device)
        s2_t = self.torch.tensor(s2, dtype=self.torch.float32, device=self.device)
        d_t = self.torch.tensor(d, dtype=self.torch.float32, device=self.device)

        q_sa = self.q(s_t).gather(1, a_t.unsqueeze(1)).squeeze(1)
        with self.torch.no_grad():
            q_next = self.q_target(s2_t).max(dim=1).values
            target = r_t + (1.0 - d_t) * float(self.cfg.gamma) * q_next

        loss = self.nn.functional.smooth_l1_loss(q_sa, target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.steps += 1
        if self.steps % int(self.cfg.target_update) == 0:
            self.q_target.load_state_dict(self.q.state_dict())

        return float(loss.item())

    def save(self, path: str) -> None:
        self.torch.save({"state_dict": self.q.state_dict(), "cfg": self.cfg.__dict__}, path)

    @classmethod
    def load(cls, path: str, *, device: Optional[str] = None):
        ts = require_torch()
        checkpoint = ts.torch.load(path, map_location=device or "cpu")
        cfg = DQNConfig(**checkpoint["cfg"])
        agent = cls(cfg=cfg, seed=0, device=device)
        agent.q.load_state_dict(checkpoint["state_dict"])
        agent.q_target.load_state_dict(agent.q.state_dict())
        return agent
