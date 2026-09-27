import torch
import torch.nn as nn
import numpy as np
from typing import List, Dict
from config import *
from agents.dqn import DQNNetwork, ReplayBuffer

class Agent1:
    """Task placement agent. Decides which fog node (or cloud) to use."""
    def __init__(self):
        self.online_net = DQNNetwork(AGENT1_STATE_DIM, AGENT1_ACTION_DIM, AGENT1_HIDDEN)
        self.target_net = DQNNetwork(AGENT1_STATE_DIM, AGENT1_ACTION_DIM, AGENT1_HIDDEN)
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.target_net.eval()
        self.optimizer = torch.optim.Adam(self.online_net.parameters(), lr=AGENT1_LR)
        self.buffer = ReplayBuffer(AGENT1_BUFFER_SIZE)
        self.epsilon = AGENT1_EPSILON_START
        self.steps = 0
        self.action_map = {0: 'FOG_A', 1: 'FOG_B', 2: 'FOG_C', 3: 'FOG_D', 4: 'CLOUD'}
        self.losses = []

    def _validate_pretrain_pairs(self, training_pairs: List[Dict]):
        """Ensure pairs are produced by TOF + MMDE-NSGA-II pipeline."""
        if not training_pairs:
            raise ValueError("Agent1 pretrain requires non-empty TOF+MMDE-NSGA-II training pairs")

        required_source = "tof-mmde-nsga2"
        for idx, pair in enumerate(training_pairs):
            if "state" not in pair or "action" not in pair:
                raise ValueError(f"Invalid training pair at index {idx}: missing state/action")

            source = pair.get("source", "")
            if source != required_source:
                raise ValueError(
                    f"Invalid training source at index {idx}: expected '{required_source}', got '{source or 'missing'}'"
                )

    def pretrain(self, training_pairs: List[Dict], epochs: int = 10):
        """Behavioral cloning from TOF + MMDE-NSGA-II expert labels only."""
        self._validate_pretrain_pairs(training_pairs)

        states = torch.FloatTensor(np.array([p['state'] for p in training_pairs]))
        actions = torch.LongTensor([p['action'] for p in training_pairs])
        criterion = nn.CrossEntropyLoss()
        for epoch in range(epochs):
            self.optimizer.zero_grad()
            q_values = self.online_net(states)
            loss = criterion(q_values, actions)
            loss.backward()
            self.optimizer.step()
        # Sync target network
        self.target_net.load_state_dict(self.online_net.state_dict())
        print(f"Pre-training complete (TOF+MMDE-NSGA-II). Final loss: {loss.item():.4f}")

    def pretrain_from_tof_mmde_nsga2(self, pebble_steps: List, fog_states: Dict, pareto_result: Dict, epochs: int = 10) -> int:
        """Build labels from TOF+MMDE-NSGA-II output and pretrain Agent1."""
        from optimizer.nsga2_mmde import extract_training_pairs

        training_pairs = extract_training_pairs(pebble_steps, fog_states, pareto_result)
        if not training_pairs:
            return 0

        self.pretrain(training_pairs, epochs=epochs)
        return len(training_pairs)

    def select_action(self, state: np.ndarray) -> int:
        """Epsilon-greedy action selection."""
        self._decay_epsilon()
        if np.random.rand() < self.epsilon:
            return np.random.randint(AGENT1_ACTION_DIM)
        with torch.no_grad():
            q = self.online_net(torch.FloatTensor(state).unsqueeze(0))
            return q.argmax().item()

    def store(self, state, action, reward, next_state, done):
        self.buffer.push(state, action, reward, next_state, done)

    def update(self):
        if len(self.buffer) < AGENT1_BATCH_SIZE:
            return
        states, actions, rewards, next_states, dones = self.buffer.sample(AGENT1_BATCH_SIZE)
        q_values = self.online_net(states).gather(1, actions.unsqueeze(1)).squeeze()
        with torch.no_grad():
            next_q = self.target_net(next_states).max(1)[0]
            targets = rewards + AGENT1_GAMMA * next_q * (1 - dones)
        loss = nn.SmoothL1Loss()(q_values, targets)
        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.online_net.parameters(), 10)
        self.optimizer.step()
        self.steps += 1
        self.losses.append(loss.item())
        if self.steps % AGENT1_TARGET_UPDATE == 0:
            self.target_net.load_state_dict(self.online_net.state_dict())

    def compute_reward(self, latency_ms: float, energy_j: float,
                       deadline_ms: float) -> float:
        """Calculate reward: balanced between latency, energy, and deadline."""
        norm_lat = min(latency_ms / deadline_ms, 3.0)
        norm_eng = min(energy_j / 0.1, 3.0)          # normalise to ~0-1
        violation = 1.0 if latency_ms > deadline_ms else 0.0
        w = AGENT1_REWARD_WEIGHTS
        R = -w['latency']*norm_lat - w['energy']*norm_eng \
            - w['violation']*violation*AGENT1_DEADLINE_PENALTY
        return float(R)

    def _decay_epsilon(self):
        self.epsilon = max(
            AGENT1_EPSILON_END,
            AGENT1_EPSILON_START - (AGENT1_EPSILON_START - AGENT1_EPSILON_END)
            * (self.steps / AGENT1_EPSILON_DECAY)
        )

    def save(self, path: str):
        torch.save({'online': self.online_net.state_dict(),
                    'target': self.target_net.state_dict(),
                    'steps': self.steps}, path)

    def load(self, path: str):
        ckpt = torch.load(path)
        self.online_net.load_state_dict(ckpt['online'])
        self.target_net.load_state_dict(ckpt['target'])
        self.steps = ckpt['steps']
