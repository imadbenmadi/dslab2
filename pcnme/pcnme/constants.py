"""
PCNME System Constants
All constants match the methodology paper exactly.
"""

# ============================================================================
# NETWORK PARAMETERS
# ============================================================================
FOG_MIPS          = 2000          # mu_k: fog node compute capacity
CLOUD_MIPS        = 8000          # mu_c: cloud compute capacity
EC_THRESHOLD      = 1.0           # theta: edge complexity threshold
Q_MAX             = 50            # aggregator task queue trigger
FOG_RADIUS        = 250.0         # R_k: fog coverage radius (metres)
BANDWIDTH_MBPS    = 100.0         # B: device-to-fog bandwidth
FOG_CLOUD_BW_MBPS = 1000.0        # B_c: fog-to-cloud backbone bandwidth
G5_LATENCY_MS     = 2.0           # delta_5G: 5G link latency
WAN_LATENCY_MS    = 30.0          # delta_WAN: WAN latency

# ============================================================================
# ENERGY MODEL
# ============================================================================
P_TX              = 0.5           # device transmit power (Watts)
KAPPA             = 0.001         # fog compute energy coefficient (J/MI)
ALPHA             = 1.8           # WAN energy penalty factor
E_REF             = 0.10          # reward normalisation reference (J)

# ============================================================================
# DEADLINE AND TIMING
# ============================================================================
TOTAL_DEADLINE_MS = 200.0         # D_tau: total task deadline

# ============================================================================
# DAG DEFINITION
# ============================================================================
DAG = {
    1: {
        "MI": 20,
        "in_KB": 8192,
        "out_KB": 200,
        "device": True,
        "deadline_ms": None,  # Step 1 is always on device
    },
    2: {
        "MI": 200,
        "in_KB": 200,
        "out_KB": 50,
        "device": False,
        "deadline_ms": 30,
    },
    3: {
        "MI": 2000,
        "in_KB": 50,
        "out_KB": 30,
        "device": False,
        "deadline_ms": 80,
    },
    4: {
        "MI": 8000,
        "in_KB": 30,
        "out_KB": 5,
        "device": False,
        "deadline_ms": 150,
    },
    5: {
        "MI": 50,
        "in_KB": 5,
        "out_KB": 1,
        "device": False,
        "deadline_ms": 200,
    },
}

# EC Classification (from methodology):
# Step 1: Device-only (always on device)
# Step 4: EC = 8000/2000 = 4.0 >= 1.0 → BOULDER → cloud
# Step 3: EC = 2000/2000 = 1.0 >= 1.0 → BOULDER → cloud
# Step 2: EC = 200/2000  = 0.1 < 1.0  → PEBBLE
# Step 5: EC = 50/2000   = 0.025 < 1.0 → PEBBLE

# ============================================================================
# FOG NODE LOCATIONS (Istanbul city zones)
# ============================================================================
FOG_NODES = {
    "A": {"pos": (200, 500), "name": "Besiktas", "initial_load": 0.30},
    "B": {"pos": (500, 200), "name": "Sisli",    "initial_load": 0.45},
    "C": {"pos": (800, 500), "name": "Kadikoy",  "initial_load": 0.35},
    "D": {"pos": (500, 800), "name": "Uskudar",  "initial_load": 0.40},
}

# ============================================================================
# OPTIMIZATION PARAMETERS (NSGA-II / MMDE)
# ============================================================================
NSGA_POP          = 100           # NSGA-II population size
NSGA_GENS         = 200           # NSGA-II generations
MMDE_F            = 0.5           # MMDE differential evolution F factor
MMDE_CR           = 0.9           # MMDE crossover rate
N_OFFLINE_BATCHES = 1000          # offline training batches for pre-training
BATCH_SIZE_NSGA   = 100           # batch size per NSGA-II offline run

# ============================================================================
# DQN PARAMETERS
# ============================================================================
STATE_DIM         = 13            # DQN state vector dimension
ACTION_DIM        = 5             # Fog A, B, C, D, Cloud
HIDDEN            = [256, 128]    # DQN network hidden layer sizes
AGENT_LR          = 0.001         # DQN learning rate
GAMMA             = 0.95          # DQN discount factor
EPSILON_START     = 0.30          # Initial exploration rate
EPSILON_MIN       = 0.05          # Minimum exploration rate
EPSILON_DECAY     = 10000         # Exploration decay steps
MINI_BATCH        = 64            # DQN mini-batch size
BUFFER_SIZE       = 50000         # Experience replay buffer size
TARGET_SYNC       = 1000          # Target network sync interval (steps)
HUBER_DELTA       = 1.0           # Huber loss delta parameter
BC_EPOCHS         = 20            # Behavioral cloning pre-training epochs
BC_LR             = 0.001         # BC learning rate
BC_THRESHOLD      = 0.05          # BC convergence threshold

# ============================================================================
# REWARD FUNCTION WEIGHTS
# ============================================================================
OMEGA_L           = 0.5           # latency weight
OMEGA_E           = 0.3           # energy weight
OMEGA_V           = 0.2           # deadline violation weight
LAMBDA_CRIT       = 10.0          # safety-critical penalty multiplier

# ============================================================================
# SIMULATION PARAMETERS
# ============================================================================
N_VEHICLES        = 50            # number of vehicles
SIM_DURATION_S    = 600.0         # simulation duration (seconds)
WARMUP_S          = 60.0          # warmup period (seconds)
N_SEEDS           = 5             # number of random seeds
SEEDS             = [42, 123, 456, 789, 2024]  # fixed seeds for reproducibility
T_EXIT_MAX        = 10.0          # max T_exit for state normalization
SPEED_MAX_MS      = 33.3          # max speed for normalization (120 km/h)

# ============================================================================
# SCENARIO SPEED DISTRIBUTIONS (from Roma taxi statistics)
# ============================================================================
SCENARIO_SPEEDS = {
    "morning_rush": {"mean": 11.0, "std": 4.0},   # congested ~40 km/h
    "off_peak":     {"mean": 16.7, "std": 3.5},   # free-flow ~60 km/h
    "evening_rush": {"mean": 9.0,  "std": 3.5},   # heavy ~32 km/h
}

# ============================================================================
# SYSTEMS TO IMPLEMENT
# ============================================================================
SYSTEMS = {
    "random":       "Random fog assignment. TOF-Broker for boulders.",
    "greedy":       "Least-loaded fog node. TOF-Broker for boulders.",
    "nsga2_static": "TOF-Broker + MMDE-NSGA-II offline. No DQN.",
    "dqn_cold":     "TOF-Broker + DQN cold start. No BC pre-training.",
    "dqn_bc_only":  "TOF-Broker + DQN BC pre-trained, frozen weights.",
    "proposed":     "Full PCNME: TOF-Broker + online DQN + proactive handoff.",
}

# ============================================================================
# VISUALIZATION STYLES
# ============================================================================
SYSTEM_STYLES = {
    "random":       {"ls": ":",  "marker": "o", "label": "Random"},
    "greedy":       {"ls": "--", "marker": "s", "label": "Greedy"},
    "nsga2_static": {"ls": "-.", "marker": "^", "label": "NSGA-II static"},
    "dqn_cold":     {"ls": "--", "marker": "D", "label": "DQN (cold start)"},
    "dqn_bc_only":  {"ls": "-.", "marker": "v", "label": "DQN (BC only)"},
    "proposed":     {"ls": "-",  "marker": "*", "label": "PCNME (proposed)",
                     "lw": 2.5},
}

# ============================================================================
# CHART CONFIGURATION
# ============================================================================
CHART_DPI          = 300
CHART_FONTSIZE     = 11
CHART_FONTFAMILY   = "Times New Roman"
CHART_FIGSIZE      = (6, 4)
