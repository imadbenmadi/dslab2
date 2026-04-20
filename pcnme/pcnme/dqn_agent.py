"""
PCNME DQN Agent
Deep Q-Network implementation for task scheduling decisions.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
from collections import deque
import warnings
from .constants import (
    STATE_DIM, ACTION_DIM, HIDDEN, AGENT_LR, GAMMA,
    EPSILON_START, EPSILON_MIN, EPSILON_DECAY, MINI_BATCH,
    BUFFER_SIZE, TARGET_SYNC, HUBER_DELTA
)
from .formulas import build_state, compute_reward, td_target, bc_loss
from .progress import progress


class DQNNetwork(nn.Module):
    """Deep Q-Network architecture."""

    def __init__(self, state_dim=STATE_DIM, action_dim=ACTION_DIM,
                 hidden_sizes=None):
        super().__init__()

        if hidden_sizes is None:
            hidden_sizes = HIDDEN

        # Build network
        layers = []
        prev_size = state_dim

        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(prev_size, hidden_size))
            layers.append(nn.ReLU())
            prev_size = hidden_size

        layers.append(nn.Linear(prev_size, action_dim))

        self.net = nn.Sequential(*layers)

    def forward(self, state):
        """Forward pass: state -> Q-values."""
        if not isinstance(state, torch.Tensor):
            state = torch.tensor(state, dtype=torch.float32)

        return self.net(state)


class ReplayBuffer:
    """Experience replay buffer for Q-learning."""

    def __init__(self, capacity=BUFFER_SIZE):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        """Add experience to buffer."""
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        """Sample random batch from buffer."""
        batch = np.random.choice(len(self.buffer), batch_size, replace=False)

        states, actions, rewards, next_states, dones = [], [], [], [], []

        for idx in batch:
            state, action, reward, next_state, done = self.buffer[idx]
            states.append(state)
            actions.append(action)
            rewards.append(reward)
            next_states.append(next_state)
            dones.append(done)

        return (
            torch.tensor(np.array(states), dtype=torch.float32),
            torch.tensor(np.array(actions), dtype=torch.long),
            torch.tensor(np.array(rewards), dtype=torch.float32),
            torch.tensor(np.array(next_states), dtype=torch.float32),
            torch.tensor(np.array(dones), dtype=torch.float32),
        )

    def __len__(self):
        return len(self.buffer)


class DQNAgent:
    """
    DQN Agent for task scheduling.
    Implements eps-greedy exploration, TD learning, target network.
    """

    def __init__(self, state_dim=STATE_DIM, action_dim=ACTION_DIM,
                 hidden_sizes=None, learning_rate=AGENT_LR):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate

        # Networks
        self.online_net = DQNNetwork(state_dim, action_dim, hidden_sizes)
        self.target_net = DQNNetwork(state_dim, action_dim, hidden_sizes)
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.target_net.eval()

        # Optimizer
        self.optimizer = optim.Adam(self.online_net.parameters(),
                                   lr=learning_rate)

        # Replay buffer
        self.replay_buffer = ReplayBuffer(BUFFER_SIZE)

        # Exploration
        self.epsilon = EPSILON_START
        self.epsilon_min = EPSILON_MIN
        self.epsilon_decay = EPSILON_DECAY
        self.global_steps = 0

        # Training
        self.loss_history = []
        self.reward_history = []

    def select_action(self, fog_state: dict, step_id: int, vehicle_id: str,
                     epsilon: float = None) -> str:
        """
        Select action (destination) using eps-greedy policy.

        Args:
            fog_state: {'loads': {...}, 'queues': {...}, 'positions': {...}}
            step_id: DAG step ID
            vehicle_id: vehicle ID
            epsilon: exploration rate (uses self.epsilon if None)

        Returns:
            destination: 'cloud', 'A', 'B', 'C', or 'D'
        """
        if epsilon is None:
            epsilon =self.epsilon

        # Build state vector
        state = build_state(
            fog_loads=fog_state['loads'],
            fog_queues=fog_state['queues'],
            step_MI=300,  # placeholder
            bw_util=0.5,  # placeholder
            vehicle_speed_ms=10.0,  # placeholder
            t_exit_s=5.0,  # placeholder
            deadline_remaining_ms=150.0,  # placeholder
        )

        # Eps-greedy
        if np.random.random() < epsilon:
            # Random action
            action_idx = np.random.randint(self.action_dim)
        else:
            # Greedy action
            state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            with torch.no_grad():
                q_values = self.online_net(state_tensor)
            action_idx = q_values.argmax(dim=1).item()

        # Map action index to destination
        action_map = {0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'cloud'}
        return action_map[action_idx]

    def store_transition(self, state, action, reward, next_state, done):
        """Store transition in replay buffer."""
        # Map action string to index
        action_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'cloud': 4}
        action_idx = action_map.get(action, 4)

        self.replay_buffer.push(state, action_idx, reward, next_state, done)

    def train_step(self, batch_size=MINI_BATCH):
        """Perform one training step on batch from replay buffer."""
        if len(self.replay_buffer) < batch_size:
            return None

        # Sample batch
        states, actions, rewards, next_states, dones = \
            self.replay_buffer.sample(batch_size)

        # Compute Q-values and TD target
        q_values = self.online_net(states)
        q_values = q_values.gather(1, actions.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            next_q_values = self.target_net(next_states)

        target = td_target(rewards, next_q_values, dones, gamma=GAMMA)

        # Huber loss
        loss = F.huber_loss(q_values, target, delta=HUBER_DELTA,
                           reduction='mean')

        # Backward
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.online_net.parameters(), 1.0)
        self.optimizer.step()

        self.loss_history.append(loss.item())
        self.global_steps += 1

        # Update epsilon
        self.epsilon = max(
            self.epsilon_min,
            self.epsilon * (1.0 - 1.0 / self.epsilon_decay)
        )

        # Sync target network
        if self.global_steps % TARGET_SYNC == 0:
            self.target_net.load_state_dict(self.online_net.state_dict())

        return loss.item()

    def pretrain_with_bc(self, dataset, epochs=20, batch_size=64):
        """
        Pre-train using Behavioral Cloning.

        Args:
            dataset: list of (state, optimal_action) tuples from NSGA-II
            epochs: number of training epochs
            batch_size: batch size
        """
        optimizer = optim.Adam(self.online_net.parameters(),
                              lr=0.001)

        dataset_size = len(dataset)
        self.bc_loss_history = []

        epoch_iter = progress(range(epochs), desc="BC pretrain", unit="epoch", total=epochs)
        for epoch in epoch_iter:
            epoch_loss = 0.0
            n_batches = 0

            for i in range(0, dataset_size, batch_size):
                batch_states = dataset[i:i + batch_size]

                if not batch_states:
                    continue

                states = torch.tensor(
                    np.array([x[0] for x in batch_states]),
                    dtype=torch.float32
                )
                actions = torch.tensor(
                    np.array([x[1] for x in batch_states]),
                    dtype=torch.long
                )

                # Forward
                q_values = self.online_net(states)

                # BC loss (cross-entropy)
                loss = bc_loss(q_values, actions)

                # Backward
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                n_batches += 1

            avg_loss = epoch_loss / max(n_batches, 1)
            self.bc_loss_history.append(avg_loss)

            if hasattr(epoch_iter, "set_postfix"):
                epoch_iter.set_postfix(loss=f"{avg_loss:.4f}")

            if (epoch + 1) % 5 == 0:
                print(f"BC Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.6f}")

    def save_weights(self, filepath):
        """Save network weights."""
        torch.save(self.online_net.state_dict(), filepath)

    def load_weights(self, filepath):
        """Load network weights."""
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"TypedStorage is deprecated.*",
                category=UserWarning,
            )
            state_dict = torch.load(filepath)

        self.online_net.load_state_dict(state_dict)
        self.target_net.load_state_dict(state_dict)

    def get_q_values(self, state):
        """Get Q-values for a state."""
        state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            q_values = self.online_net(state_tensor)
        return q_values.squeeze(0).detach().numpy()
