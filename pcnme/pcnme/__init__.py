"""
PCNME - Proactive Computing for Network-embedded Mobile Environments
A comprehensive fog-cloud computing optimization framework.

Mathematical formulas and implementations taken directly from the research
methodology paper.
"""

__version__ = "1.0.0"

# Import all constants explicitly
from .constants import (
    FOG_MIPS, CLOUD_MIPS, EC_THRESHOLD, Q_MAX, FOG_RADIUS,
    BANDWIDTH_MBPS, FOG_CLOUD_BW_MBPS, G5_LATENCY_MS, WAN_LATENCY_MS,
    P_TX, KAPPA, ALPHA, E_REF, TOTAL_DEADLINE_MS,
    DAG, FOG_NODES, NSGA_POP, NSGA_GENS, MMDE_F, MMDE_CR,
    N_OFFLINE_BATCHES, BATCH_SIZE_NSGA,
    STATE_DIM, ACTION_DIM, HIDDEN, AGENT_LR, GAMMA,
    EPSILON_START, EPSILON_MIN, EPSILON_DECAY,
    MINI_BATCH, BUFFER_SIZE, TARGET_SYNC, HUBER_DELTA,
    BC_EPOCHS, BC_LR, BC_THRESHOLD,
    OMEGA_L, OMEGA_E, OMEGA_V, LAMBDA_CRIT,
    N_VEHICLES, SIM_DURATION_S, WARMUP_S, N_SEEDS, SEEDS,
    T_EXIT_MAX, SPEED_MAX_MS, SCENARIO_SPEEDS, SYSTEMS
)
from .formulas import *
from .metrics import TaskRecord, MetricsCollector, SystemSummary
from .data_generation import DataManager, synthetic_traces
from .simulation import SimulationEnvironment, FogNode, Vehicle
from .systems import create_system
from .dqn_agent import DQNAgent, DQNNetwork, ReplayBuffer
from .optimization import NSGAIIOptimizer, MMDEOptimizer, generate_bc_dataset_from_nsga2
from .analysis import ResultsAnalyzer

__all__ = [
    # Classes and functions
    'TaskRecord',
    'MetricsCollector',
    'SystemSummary',
    'DataManager',
    'synthetic_traces',
    'SimulationEnvironment',
    'FogNode',
    'Vehicle',
    'create_system',
    'DQNAgent',
    'DQNNetwork',
    'ReplayBuffer',
    'NSGAIIOptimizer',
    'MMDEOptimizer',
    'generate_bc_dataset_from_nsga2',
    'ResultsAnalyzer',
    # Constants (from .constants import *)
    'FOG_MIPS',
    'CLOUD_MIPS',
    'EC_THRESHOLD',
    'Q_MAX',
    'FOG_RADIUS',
    'BANDWIDTH_MBPS',
    'FOG_CLOUD_BW_MBPS',
    'G5_LATENCY_MS',
    'WAN_LATENCY_MS',
    'P_TX',
    'KAPPA',
    'ALPHA',
    'E_REF',
    'TOTAL_DEADLINE_MS',
    'DAG',
    'FOG_NODES',
    'NSGA_POP',
    'NSGA_GENS',
    'MMDE_F',
    'MMDE_CR',
    'N_OFFLINE_BATCHES',
    'BATCH_SIZE_NSGA',
    'STATE_DIM',
    'ACTION_DIM',
    'HIDDEN',
    'AGENT_LR',
    'GAMMA',
    'EPSILON_START',
    'EPSILON_MIN',
    'EPSILON_DECAY',
    'MINI_BATCH',
    'BUFFER_SIZE',
    'TARGET_SYNC',
    'HUBER_DELTA',
    'BC_EPOCHS',
    'BC_LR',
    'BC_THRESHOLD',
    'OMEGA_L',
    'OMEGA_E',
    'OMEGA_V',
    'LAMBDA_CRIT',
    'N_VEHICLES',
    'SIM_DURATION_S',
    'WARMUP_S',
    'N_SEEDS',
    'SEEDS',
    'T_EXIT_MAX',
    'SPEED_MAX_MS',
    'SCENARIO_SPEEDS',
    'SYSTEMS',
]
