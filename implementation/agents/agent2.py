import torch
import torch.nn as nn
import numpy as np
from config import *
from agents.dqn import DQNNetwork, ReplayBuffer

class Agent2:
    """SDN routing agent. Manages network path selection and QoS."""
    def __init__(self):
        self.online_net = DQNNetwork(AGENT2_STATE_DIM, AGENT2_ACTION_DIM, AGENT2_HIDDEN)
        self.target_net = DQNNetwork(AGENT2_STATE_DIM, AGENT2_ACTION_DIM, AGENT2_HIDDEN)
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.target_net.eval()
        self.optimizer = torch.optim.Adam(self.online_net.parameters(), lr=AGENT2_LR)
        self.buffer = ReplayBuffer(AGENT2_BUFFER_SIZE)
        self.epsilon = AGENT2_EPSILON_START
        self.steps = 0
        self.preinstalled_rules = {}    # path -> expiry_time
        self.action_map = {
            0: 'PRIMARY_PATH',
            1: 'ALT_PATH_1',
            2: 'ALT_PATH_2',
            3: 'RESERVE_VIP',
            4: 'BEST_EFFORT',
        }

    def select_action(self, state: np.ndarray) -> int:
        self._decay_epsilon()
        if np.random.rand() < self.epsilon:
            return np.random.randint(AGENT2_ACTION_DIM)
        with torch.no_grad():
            q = self.online_net(torch.FloatTensor(state).unsqueeze(0))
            return q.argmax().item()

    def preinstall_vip_lane(self, path: str, sim_time: float, duration: float = 10.0):
        """Pre-install network rules to minimize latency."""
        self.preinstalled_rules[path] = sim_time + duration
        return True

    def route_flow(self, path_request: str, sim_time: float) -> tuple:
        """Route traffic flow. Returns (path, overhead_ms)."""
        if path_request in self.preinstalled_rules:
            if self.preinstalled_rules[path_request] > sim_time:
                return path_request, 0.0      # pre-installed hit!
        # Reactive: 8-15ms controller overhead
        overhead = np.random.uniform(8, 15)
        return path_request, overhead

    def compute_reward(self, delivery_ratio: float, routing_delay_ms: float,
                       ctrl_overhead_ms: float, packet_drop: bool,
                       preinstall_hit: bool) -> float:
        w = AGENT2_REWARD_WEIGHTS
        R = (w['delivery'] * delivery_ratio
             - w['delay'] * min(routing_delay_ms / 50.0, 1.0)
             - w['overhead'] * min(ctrl_overhead_ms / 15.0, 1.0))
        if packet_drop:
            R -= AGENT2_PACKET_DROP_PENALTY
        if preinstall_hit:
            R += AGENT2_PREINSTALL_BONUS
        return float(R)

    def store(self, state, action, reward, next_state, done):
        self.buffer.push(state, action, reward, next_state, done)

    def update(self):
        if len(self.buffer) < AGENT2_BATCH_SIZE:
            return
        states, actions, rewards, next_states, dones = self.buffer.sample(AGENT2_BATCH_SIZE)
        q_values = self.online_net(states).gather(1, actions.unsqueeze(1)).squeeze()
        with torch.no_grad():
            next_q = self.target_net(next_states).max(1)[0]
            targets = rewards + AGENT2_GAMMA * next_q * (1 - dones)
        loss = nn.SmoothL1Loss()(q_values, targets)
        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.online_net.parameters(), 10)
        self.optimizer.step()
        self.steps += 1
        if self.steps % AGENT2_TARGET_UPDATE == 0:
            self.target_net.load_state_dict(self.online_net.state_dict())

    def _decay_epsilon(self):
        self.epsilon = max(
            AGENT2_EPSILON_END,
            AGENT2_EPSILON_START - (AGENT2_EPSILON_START - AGENT2_EPSILON_END)
            * (self.steps / AGENT2_EPSILON_DECAY)
        )

    def save(self, path: str):
        torch.save({'online': self.online_net.state_dict(),
                    'target': self.target_net.state_dict(),
                    'steps': self.steps}, path)
