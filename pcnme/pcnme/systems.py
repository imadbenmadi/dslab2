"""
PCNME System Implementations
Six different task scheduling systems for comparison.
"""

import numpy as np
from abc import ABC, abstractmethod
from .constants import FOG_NODES, EC_THRESHOLD, STATE_DIM, ACTION_DIM
from .formulas import (
    classify_step, compute_ec, compute_t_exit,
    select_handoff_mode, build_state, compute_reward
)


class BaseSystem(ABC):
    """Abstract base class for all systems."""

    def __init__(self, system_name: str, env=None):
        self.system_name = system_name
        self.env = env
        self.decisions = []
        self.handoff_events = []

    @abstractmethod
    def select_destination(self, step_id: int, vehicle_id: str,
                          fog_state: dict) -> str:
        """
        Select execution destination for a step.
        
        Args:
            step_id: DAG step (1-5)
            vehicle_id: vehicle ID
            fog_state: {'loads': {...}, 'queues': {...}, 'positions': {...}}
        
        Returns:
            'cloud' or fog node ID ('A', 'B', 'C', 'D')
        """
        pass

    def record_decision(self, task_id: str, step_id: int, decision: str):
        """Record a scheduling decision."""
        self.decisions.append({
            'task_id': task_id,
            'step_id': step_id,
            'destination': decision,
            'timestamp_s': self.env.sim_time_s if self.env else 0.0,
        })

    def record_handoff(self, vehicle_id: str, success: bool, mode: str):
        """Record a handoff event."""
        self.handoff_events.append({
            'vehicle_id': vehicle_id,
            'success': success,
            'mode': mode,
            'timestamp_s': self.env.sim_time_s if self.env else 0.0,
        })


# ============================================================================
# BASELINE SYSTEMS
# ============================================================================

class RandomSystem(BaseSystem):
    """Random fog assignment. TOF-Broker for boulders only."""

    def __init__(self, env=None, seed=42):
        super().__init__('random', env)
        self.rng = np.random.default_rng(seed)

    def select_destination(self, step_id: int, vehicle_id: str,
                          fog_state: dict) -> str:
        """
        Random selection: cloud for boulders, random fog for pebbles.
        """
        step_class = classify_step(300 if step_id == 4 else 50)  # simplified

        if step_class == 'boulder':
            return 'cloud'
        else:
            return self.rng.choice(list(FOG_NODES.keys()))


class GreedySystem(BaseSystem):
    """Least-loaded fog node. TOF-Broker for boulders only."""

    def select_destination(self, step_id: int, vehicle_id: str,
                          fog_state: dict) -> str:
        """
        Greedy: cloud for boulders, least-loaded fog for pebbles.
        """
        step_class = classify_step(300 if step_id == 4 else 50)

        if step_class == 'boulder':
            return 'cloud'
        else:
            # Choose least-loaded fog node
            best_fog = min(fog_state['loads'], key=fog_state['loads'].get)
            return best_fog


class NSGA2StaticSystem(BaseSystem):
    """TOF-Broker + MMDE-NSGA-II offline. No DQN. No proactive handoff."""

    def __init__(self, env=None, precomputed_table=None):
        super().__init__('nsga2_static', env)
        self.precomputed_table = precomputed_table or {}

    def set_precomputed_table(self, table: dict):
        """Set precomputed routing table from offline optimization."""
        self.precomputed_table = table

    def select_destination(self, step_id: int, vehicle_id: str,
                          fog_state: dict) -> str:
        """
        Look up destination from precomputed NSGA-II solution.
        Fall back to greedy if table missing.
        """
        key = (step_id, vehicle_id)

        if key in self.precomputed_table:
            return self.precomputed_table[key]
        else:
            # Fallback: greedy
            step_class = classify_step(300 if step_id == 4 else 50)
            if step_class == 'boulder':
                return 'cloud'
            else:
                best_fog = min(fog_state['loads'], key=fog_state['loads'].get)
                return best_fog


# ============================================================================
# LEARNING-BASED SYSTEMS
# ============================================================================

class DQNColdStartSystem(BaseSystem):
    """TOF-Broker + DQN from random init. No BC pre-training. Online updates ON."""

    def __init__(self, env=None, dqn_agent=None):
        super().__init__('dqn_cold', env)
        self.dqn_agent = dqn_agent  # DQN agent instance
        self.epsilon = 0.3  # initial exploration

    def set_dqn_agent(self, agent):
        """Set the DQN agent."""
        self.dqn_agent = agent

    def select_destination(self, step_id: int, vehicle_id: str,
                          fog_state: dict) -> str:
        """
        Use DQN agent to select destination.
        Cold start: no BC pre-training, online updates active.
        """
        if self.dqn_agent is None:
            # Fallback to greedy
            step_class = classify_step(300 if step_id == 4 else 50)
            if step_class == 'boulder':
                return 'cloud'
            else:
                best_fog = min(fog_state['loads'], key=fog_state['loads'].get)
                return best_fog

        # Use DQN for decision
        return self.dqn_agent.select_action(
            fog_state, step_id, vehicle_id, epsilon=self.epsilon
        )


class DQNBCOnlySystem(BaseSystem):
    """DQN pre-trained via BC but weights FROZEN. No online updates."""

    def __init__(self, env=None, dqn_agent=None):
        super().__init__('dqn_bc_only', env)
        self.dqn_agent = dqn_agent
        self.epsilon = 0.05  # low exploration after BC pre-training

    def set_dqn_agent(self, agent):
        """Set pre-trained DQN agent."""
        self.dqn_agent = agent
        # Freeze weights
        if hasattr(agent, 'online_net'):
            for param in agent.online_net.parameters():
                param.requires_grad = False

    def select_destination(self, step_id: int, vehicle_id: str,
                          fog_state: dict) -> str:
        """
        Use frozen BC-pre-trained DQN.
        Demonstrates value of BC pre-training without online fine-tuning.
        """
        if self.dqn_agent is None:
            step_class = classify_step(300 if step_id == 4 else 50)
            if step_class == 'boulder':
                return 'cloud'
            else:
                best_fog = min(fog_state['loads'], key=fog_state['loads'].get)
                return best_fog

        return self.dqn_agent.select_action(
            fog_state, step_id, vehicle_id, epsilon=self.epsilon
        )


class ProposedSystem(BaseSystem):
    """
    Full PCNME: TOF-Broker + Aggregator + NSGA-II pre-training +
    online DQN + proactive handoff + NTB/HTB.
    """

    def __init__(self, env=None, dqn_agent=None):
        super().__init__('proposed', env)
        self.dqn_agent = dqn_agent
        self.epsilon = 0.3
        self.use_proactive_handoff = True
        self.aggregator_queue_threshold = 50

    def set_dqn_agent(self, agent):
        """Set DQN agent with BC pre-training."""
        self.dqn_agent = agent

    def select_destination(self, step_id: int, vehicle_id: str,
                          fog_state: dict) -> str:
        """
        Full system: DQN with online learning + proactive handoff.
        """
        # Classify step
        step_class = classify_step(300 if step_id == 4 else 50)

        # Boulders always go to cloud
        if step_class == 'boulder':
            return 'cloud'

        # For pebbles: use DQN if available
        if self.dqn_agent is None:
            # Fallback: greedy
            best_fog = min(fog_state['loads'], key=fog_state['loads'].get)
            return best_fog

        # DQN selects destination
        return self.dqn_agent.select_action(
            fog_state, step_id, vehicle_id, epsilon=self.epsilon
        )

    def should_trigger_aggregator(self, fog_state: dict) -> bool:
        """
        Check if aggregator should trigger.
        Aggregator groups multiple pebbles into one batch.
        """
        for queue_len in fog_state['queues'].values():
            if queue_len >= self.aggregator_queue_threshold:
                return True
        return False

    def apply_proactive_handoff_logic(self, vehicle_id: str,
                                     step_id: int, fog_node_id: str) -> dict:
        """
        Apply proactive handoff: execute before leaving coverage if needed.
        
        Returns:
            {'handoff_triggered': bool, 'mode': str, 'success': bool}
        """
        if not self.use_proactive_handoff or self.env is None:
            return {'handoff_triggered': False, 'mode': 'none', 'success': False}

        # Compute T_exit to this fog node
        t_exit_s = self.env.compute_t_exit_to_fog(vehicle_id, fog_node_id)

        # Compute execution time (simplified: assume 100ms)
        t_exec_s = 0.1  # 100ms

        # Select mode
        mode = select_handoff_mode(t_exec_s * 1000, t_exit_s)

        if mode == 'proactive' and t_exit_s < float('inf'):
            # Trigger proactive handoff
            return {
                'handoff_triggered': True,
                'mode': 'proactive',
                'success': True,  # simplified: assume success
            }
        else:
            return {
                'handoff_triggered': False,
                'mode': 'direct',
                'success': True,
            }


# ============================================================================
# SYSTEM FACTORY
# ============================================================================

def create_system(system_name: str, env=None, dqn_agent=None,
                  precomputed_table=None, seed=42) -> BaseSystem:
    """
    Factory function to create system instances.
    
    Args:
        system_name: 'random', 'greedy', 'nsga2_static', 'dqn_cold',
                     'dqn_bc_only', or 'proposed'
        env: simulation environment
        dqn_agent: DQN agent for learning-based systems
        precomputed_table: precomputed decisions for NSGA-II
        seed: random seed
    
    Returns:
        System instance
    """
    if system_name == 'random':
        return RandomSystem(env, seed)
    elif system_name == 'greedy':
        return GreedySystem(env)
    elif system_name == 'nsga2_static':
        sys = NSGA2StaticSystem(env, precomputed_table)
        return sys
    elif system_name == 'dqn_cold':
        return DQNColdStartSystem(env, dqn_agent)
    elif system_name == 'dqn_bc_only':
        return DQNBCOnlySystem(env, dqn_agent)
    elif system_name == 'proposed':
        return ProposedSystem(env, dqn_agent)
    else:
        raise ValueError(f"Unknown system: {system_name}")
