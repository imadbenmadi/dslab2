"""
PCNME Package - Proactive Computing for Network-Embedded Mobile Environments
"""

from .constants import (
    FOG_MIPS, CLOUD_MIPS, EC_THRESHOLD, DAG, FOG_NODES,
    SYSTEMS, SCENARIOS, SEEDS, N_SEEDS, NSGA_GENS, NSGA_POP,
    STATE_DIM, ACTION_DIM, HIDDEN, BC_THRESHOLD, N_OFFLINE_BATCHES,
    SCENARIO_SPEEDS, N_VEHICLES, SIM_DURATION_S, WARMUP_S,
    BATCH_SIZE_NSGA, AGENT_LR, GAMMA, EPSILON_START, EPSILON_MIN,
    EPSILON_DECAY, MINI_BATCH, BUFFER_SIZE, TARGET_SYNC, HUBER_DELTA,
    BC_EPOCHS, BC_LR, OMEGA_L, OMEGA_E, OMEGA_V, LAMBDA_CRIT,
    T_EXIT_MAX, SPEED_MAX_MS, FOG_RADIUS, BANDWIDTH_MBPS,
    FOG_CLOUD_BW_MBPS, G5_LATENCY_MS, WAN_LATENCY_MS, P_TX, KAPPA,
    ALPHA, E_REF, TOTAL_DEADLINE_MS, Q_MAX, MMDE_F, MMDE_CR
)

from .formulas import (
    compute_ec, classify_step,
    t_exec_fog, t_exec_cloud, t_tx_fog, t_tx_cloud,
    step_latency, step_energy,
    compute_v_closing, compute_t_exit, select_handoff_mode,
    build_state, compute_reward,
    td_target, huber_loss, bc_loss,
    feasibility_rate, bootstrap_ci, wilcoxon_test
)

from .metrics import TaskRecord, MetricsCollector, SystemSummary

from .data_generation import (
    synthetic_traces, load_roma_taxi_dataset, load_sf_cabspotting,
    DataManager
)

from .simulation import (
    FogNode, Vehicle, SimulationEnvironment,
    CloudSimulator, TaskExecutor
)

from .systems import (
    BaseSystem, RandomSystem, GreedySystem,
    NSGA2StaticSystem, DQNColdStartSystem, DQNBCOnlySystem,
    ProposedSystem, create_system
)

from .dqn_agent import DQNNetwork, ReplayBuffer, DQNAgent

from .optimization import (
    SchedulingProblem, NSGAIIOptimizer, MMDEOptimizer,
    generate_bc_dataset_from_nsga2
)

from .analysis import ResultsAnalyzer

__all__ = [
    # Constants
    "FOG_MIPS", "CLOUD_MIPS", "EC_THRESHOLD", "DAG", "FOG_NODES",
    "SYSTEMS", "SCENARIOS", "SEEDS", "N_SEEDS",
    "STATE_DIM", "ACTION_DIM", "HIDDEN", "BC_THRESHOLD", "N_OFFLINE_BATCHES",
    "SCENARIO_SPEEDS", "N_VEHICLES", "SIM_DURATION_S", "WARMUP_S",
    "BATCH_SIZE_NSGA", "AGENT_LR", "GAMMA", "EPSILON_START", "EPSILON_MIN",
    "EPSILON_DECAY", "MINI_BATCH", "BUFFER_SIZE", "TARGET_SYNC", "HUBER_DELTA",
    "BC_EPOCHS", "BC_LR", "OMEGA_L", "OMEGA_E", "OMEGA_V", "LAMBDA_CRIT",
    "T_EXIT_MAX", "SPEED_MAX_MS", "FOG_RADIUS", "BANDWIDTH_MBPS",
    "FOG_CLOUD_BW_MBPS", "G5_LATENCY_MS", "WAN_LATENCY_MS", "P_TX", "KAPPA",
    "ALPHA", "E_REF", "TOTAL_DEADLINE_MS", "Q_MAX", "MMDE_F", "MMDE_CR",
    "NSGA_GENS", "NSGA_POP",
    # Formulas
    "compute_ec", "classify_step",
    "t_exec_fog", "t_exec_cloud", "t_tx_fog", "t_tx_cloud",
    "step_latency", "step_energy",
    "compute_v_closing", "compute_t_exit", "select_handoff_mode",
    "build_state", "compute_reward",
    "td_target", "huber_loss", "bc_loss",
    "feasibility_rate", "bootstrap_ci", "wilcoxon_test",
    # Metrics
    "TaskRecord", "MetricsCollector", "SystemSummary",
    # Data generation
    "synthetic_traces", "load_roma_taxi_dataset", "load_sf_cabspotting",
    "DataManager",
    # Simulation
    "FogNode", "Vehicle", "SimulationEnvironment",
    "CloudSimulator", "TaskExecutor",
    # Systems
    "BaseSystem", "RandomSystem", "GreedySystem",
    "NSGA2StaticSystem", "DQNColdStartSystem", "DQNBCOnlySystem",
    "ProposedSystem", "create_system",
    # DQN
    "DQNNetwork", "ReplayBuffer", "DQNAgent",
    # Optimization
    "SchedulingProblem", "NSGAIIOptimizer", "MMDEOptimizer",
    "generate_bc_dataset_from_nsga2",
    # Analysis
    "ResultsAnalyzer",
]

__version__ = "1.0.0"
__author__ = "PCNME Research Team"
