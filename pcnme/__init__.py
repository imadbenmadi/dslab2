"""
PCNME - Predictive Cloud-Native Mobile Edge Framework
Mathematical formulas and implementations based on the research methodology paper.
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "PCNME Research Team (Eötvös Loránd University - Data Science)"

# ============================================================================
# CORE FRAMEWORK EXPORTS
# ============================================================================

# Constants: System parameters (all from methodology paper Table 1)
from .constants import (
    # Network parameters
    FOG_MIPS, CLOUD_MIPS, FOG_RADIUS, BANDWIDTH_MBPS, FOG_CLOUD_BW_MBPS,
    G5_LATENCY_MS, WAN_LATENCY_MS,
    # Energy model
    P_TX, KAPPA, ALPHA, E_REF,
    # Constraints
    EC_THRESHOLD, Q_MAX, TOTAL_DEADLINE_MS,
    # DAG and topology
    DAG, FOG_NODES,
    # Optimization
    NSGA_POP, NSGA_GENS, MMDE_F, MMDE_CR, N_OFFLINE_BATCHES, BATCH_SIZE_NSGA,
    # DQN hyperparameters
    STATE_DIM, ACTION_DIM, HIDDEN, AGENT_LR, GAMMA, EPSILON_START, EPSILON_MIN,
    EPSILON_DECAY, MINI_BATCH, BUFFER_SIZE, TARGET_SYNC, HUBER_DELTA,
    BC_EPOCHS, BC_LR, BC_THRESHOLD,
    # Reward weights
    OMEGA_L, OMEGA_E, OMEGA_V, LAMBDA_CRIT,
    # Simulation
    N_VEHICLES, SIM_DURATION_S, WARMUP_S, N_SEEDS, SEEDS, T_EXIT_MAX, SPEED_MAX_MS,
    SCENARIO_SPEEDS, SYSTEMS,
)

# Mathematical formulas (from methodology Section 3-5)
from .formulas import (
    compute_ec, classify_step,
    t_exec_fog, t_exec_cloud, t_tx_fog, t_tx_cloud,
    step_latency, step_energy,
    compute_v_closing, compute_t_exit, select_handoff_mode,
    build_state, compute_reward,
)

# Metrics and data structures
from .metrics import TaskRecord, MetricsCollector, SystemSummary

# Data generation and management
from .data_generation import DataManager

# Simulation environment
from .simulation import FogNode, Vehicle, SimulationEnvironment, CloudSimulator, TaskExecutor

# System implementations (6 baseline/proposed systems)
from .systems import (
    BaseSystem, RandomSystem, GreedySystem,
    NSGA2StaticSystem, DQNColdStartSystem, DQNBCOnlySystem,
    ProposedSystem, create_system
)

# DQN agent and components
from .dqn_agent import DQNNetwork, ReplayBuffer, DQNAgent

# Multi-objective optimization
from .optimization import (
    SchedulingProblem, NSGAIIOptimizer, MMDEOptimizer,
    generate_bc_dataset_from_nsga2
)

# Results analysis
from .analysis import ResultsAnalyzer

# Utilities (logging, data generation)
from . import utilities

__all__ = [
    # Constants
    "FOG_MIPS", "CLOUD_MIPS", "FOG_RADIUS", "BANDWIDTH_MBPS", "FOG_CLOUD_BW_MBPS",
    "G5_LATENCY_MS", "WAN_LATENCY_MS", "P_TX", "KAPPA", "ALPHA", "E_REF",
    "EC_THRESHOLD", "Q_MAX", "TOTAL_DEADLINE_MS", "DAG", "FOG_NODES",
    "NSGA_POP", "NSGA_GENS", "MMDE_F", "MMDE_CR", "N_OFFLINE_BATCHES",
    "STATE_DIM", "ACTION_DIM", "HIDDEN", "AGENT_LR", "GAMMA", "EPSILON_START",
    "EPSILON_MIN", "EPSILON_DECAY", "MINI_BATCH", "BUFFER_SIZE", "TARGET_SYNC",
    "HUBER_DELTA", "BC_EPOCHS", "BC_LR", "BC_THRESHOLD", "OMEGA_L", "OMEGA_E",
    "OMEGA_V", "LAMBDA_CRIT", "N_VEHICLES", "SIM_DURATION_S", "WARMUP_S",
    "N_SEEDS", "SEEDS", "T_EXIT_MAX", "SPEED_MAX_MS", "SCENARIO_SPEEDS", "SYSTEMS",
    # Formulas
    "compute_ec", "classify_step", "t_exec_fog", "t_exec_cloud",
    "t_tx_fog", "t_tx_cloud", "step_latency", "step_energy",
    "compute_v_closing", "compute_t_exit", "select_handoff_mode",
    "build_state", "compute_reward",
    # Metrics
    "TaskRecord", "MetricsCollector", "SystemSummary",
    # Data
    "DataManager",
    # Simulation
    "FogNode", "Vehicle", "SimulationEnvironment", "CloudSimulator", "TaskExecutor",
    # Systems
    "BaseSystem", "RandomSystem", "GreedySystem", "NSGA2StaticSystem",
    "DQNColdStartSystem", "DQNBCOnlySystem", "ProposedSystem", "create_system",
    # DQN
    "DQNNetwork", "ReplayBuffer", "DQNAgent",
    # Optimization
    "SchedulingProblem", "NSGAIIOptimizer", "MMDEOptimizer",
    "generate_bc_dataset_from_nsga2",
    # Analysis
    "ResultsAnalyzer",
    # Utilities
    "utilities",
]
