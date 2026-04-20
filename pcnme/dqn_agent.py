"""
DQN Agent with behavioral cloning pre-training.
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import warnings
from pathlib import Path
from typing import Tuple, List

from .constants import (
    STATE_DIM, ACTION_DIM, HIDDEN, AGENT_LR, GAMMA,
    EPSILON_START, EPSILON_MIN, EPSILON_DECAY, MINI_BATCH,
    BUFFER_SIZE, TARGET_SYNC, HUBER_DELTA
)
from .formulas import huber_loss, bc_loss


class DQNNetwork(nn.Module):
    """Deep Q-Network."""

    def __init__(self, state_dim: int = STATE_DIM, action_dim: int = ACTION_DIM,
                 hidden_sizes: List[int] = None):
        super().__init__()
        if hidden_sizes is None:
            hidden_sizes = HIDDEN

        layers = []
        prev_size = state_dim
        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(prev_size, hidden_size))
            layers.append(nn.ReLU())
            prev_size = hidden_size
        layers.append(nn.Linear(prev_size, action_dim))

        self.net = nn.Sequential(*layers)

    def forward(self, state):
        """Forward pass."""
        if isinstance(state, list):
            state = torch.tensor(state, dtype=torch.float32)
        elif not isinstance(state, torch.Tensor):
            state = torch.tensor(state, dtype=torch.float32)
        if state.dim() == 1:
            state = state.unsqueeze(0)
        return self.net(state)


class ReplayBuffer:
    """Experience replay buffer."""

    def __init__(self, max_size: int = BUFFER_SIZE):
        self.max_size = max_size
        self.buffer = []
        self.position = 0

    def add(self, state, action, reward, next_state, done):
        """Add experience to buffer."""
        experience = (state, action, reward, next_state, done)
        if len(self.buffer) < self.max_size:
            self.buffer.append(experience)
        else:
            self.buffer[self.position] = experience
        self.position = (self.position + 1) % self.max_size

    def sample(self, batch_size: int):
        """Sample mini-batch."""
        indices = np.random.choice(len(self.buffer), batch_size, replace=False)
        states, actions, rewards, next_states, dones = zip(*[self.buffer[i] for i in indices])
        return states, actions, rewards, next_states, dones

    def __len__(self):
        return len(self.buffer)


class DQNAgent:
    """DQN agent with online learning and behavioral cloning."""

    def __init__(self, state_dim: int = STATE_DIM, action_dim: int = ACTION_DIM,
                 learning_rate: float = AGENT_LR, gamma: float = GAMMA):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate
        self.gamma = gamma

        self.online_net = DQNNetwork(state_dim, action_dim)
        self.target_net = DQNNetwork(state_dim, action_dim)
        self.target_net.load_state_dict(self.online_net.state_dict())

        self.optimizer = optim.Adam(self.online_net.parameters(), lr=learning_rate)
        self.replay_buffer = ReplayBuffer()

        self.epsilon = EPSILON_START
        self.epsilon_decay = EPSILON_DECAY
        self.steps = 0

    def select_action(self, state, training: bool = True) -> int:
        """Select action with epsilon-greedy policy."""
        if training and np.random.random() < self.epsilon:
            return np.random.randint(self.action_dim)

        with torch.no_grad():
            q_values = self.online_net(state)
        return int(q_values.argmax(dim=1).item())

    def train_step(self) -> float:
        """Perform one training step."""
        if len(self.replay_buffer) < MINI_BATCH:
            return 0.0

        states, actions, rewards, next_states, dones = self.replay_buffer.sample(MINI_BATCH)

        q_values = self.online_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            next_q_values = self.target_net(next_states).max(dim=1)[0]
            td_targets = rewards + self.gamma * next_q_values * (1.0 - dones)

        loss = huber_loss(q_values, td_targets, delta=HUBER_DELTA)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.steps += 1
        self.epsilon = EPSILON_MIN + (EPSILON_START - EPSILON_MIN) * \
                      np.exp(-self.steps / self.epsilon_decay)

        if self.steps % TARGET_SYNC == 0:
            self.target_net.load_state_dict(self.online_net.state_dict())

        return float(loss.item())

    def pretrain_with_bc(self, bc_dataset: List[Tuple], epochs: int = 20,
                        batch_size: int = 32) -> float:
        """Pre-train with behavioral cloning."""
        optimizer = optim.Adam(self.online_net.parameters(), lr=0.001)
        final_loss = 0.0

        for epoch in range(epochs):
            epoch_loss = 0.0
            n_batches = 0

            for i in range(0, len(bc_dataset), batch_size):
                batch = bc_dataset[i:i + batch_size]
                states = torch.tensor(np.array([s for s, _ in batch]), dtype=torch.float32)
                actions = torch.tensor(np.array([a for _, a in batch]), dtype=torch.long)

                q_values = self.online_net(states)
                loss = bc_loss(q_values, actions)

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                epoch_loss += float(loss.item())
                n_batches += 1

            avg_loss = epoch_loss / max(n_batches, 1)
            final_loss = avg_loss

        return final_loss

    def save_weights(self, filepath: Path) -> None:
        """Save network weights."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.online_net.state_dict(), filepath)

    def load_weights(self, filepath: Path) -> None:
        """Load network weights."""
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"TypedStorage is deprecated.*",
                category=UserWarning,
            )
            state_dict = torch.load(filepath, weights_only=True)

        self.online_net.load_state_dict(state_dict)
        self.target_net.load_state_dict(self.online_net.state_dict())
