"""
PCNME Constants — Single source of truth for all system parameters.
All values match the methodology paper exactly.
"""

# Core system parameters
FOG_MIPS = 2000  # mu_k
CLOUD_MIPS = 8000  # mu_c
EC_THRESHOLD = 1.0  # theta
Q_MAX = 50  # aggregator trigger
FOG_RADIUS = 250.0  # R_k in metres
BANDWIDTH_MBPS = 100.0  # B (5G upload)
FOG_CLOUD_BW_MBPS = 1000.0  # B_c
G5_LATENCY_MS = 2.0  # delta_5G
WAN_LATENCY_MS = 30.0  # delta_WAN
P_TX = 0.5  # transmit power (W)
KAPPA = 0.001  # fog compute energy (J/MI)
ALPHA = 1.8  # WAN energy penalty
E_REF = 0.10  # reward energy reference (J)
TOTAL_DEADLINE_MS = 200.0  # D_tau

# DAG task specification (5 steps)
DAG = {
    1: {"MI": 20, "in_KB": 8192, "out_KB": 200, "device": True, "deadline_ms": None},
    2: {"MI": 200, "in_KB": 200, "out_KB": 50, "device": False, "deadline_ms": 30},
    3: {"MI": 2000, "in_KB": 50, "out_KB": 30, "device": False, "deadline_ms": 80},
    4: {"MI": 8000, "in_KB": 30, "out_KB": 5, "device": False, "deadline_ms": 150},
    5: {"MI": 50, "in_KB": 5, "out_KB": 1, "device": False, "deadline_ms": 200},
}

# EC classification for each step
# Step 2: EC = 200/2000 = 0.1 < 1.0 → PEBBLE
# Step 3: EC = 2000/2000 = 1.0 >= 1.0 → BOULDER
# Step 4: EC = 8000/2000 = 4.0 >= 1.0 → BOULDER
# Step 5: EC = 50/2000 = 0.025 < 1.0 → PEBBLE

# Fog nodes (Istanbul locations)
FOG_NODES = {
    "A": {"pos": (200, 500), "name": "Besiktas", "initial_load": 0.30},
    "B": {"pos": (500, 200), "name": "Sisli", "initial_load": 0.45},
    "C": {"pos": (800, 500), "name": "Kadikoy", "initial_load": 0.35},
    "D": {"pos": (500, 800), "name": "Uskudar", "initial_load": 0.40},
}

# NSGA-II / MMDE optimization
NSGA_POP = 100
NSGA_GENS = 200
MMDE_F = 0.5
MMDE_CR = 0.9
N_OFFLINE_BATCHES = 1000
BATCH_SIZE_NSGA = 100

# DQN configuration
STATE_DIM = 13
ACTION_DIM = 5  # Fog A, B, C, D, Cloud
HIDDEN = [256, 128]
AGENT_LR = 0.001
GAMMA = 0.95
EPSILON_START = 0.30
EPSILON_MIN = 0.05
EPSILON_DECAY = 10000
MINI_BATCH = 64
BUFFER_SIZE = 50000
TARGET_SYNC = 1000
HUBER_DELTA = 1.0
BC_EPOCHS = 20
BC_LR = 0.001
BC_THRESHOLD = 0.05  # epsilon_BC: stop pre-training when loss < this

# Reward weights
OMEGA_L = 0.5
OMEGA_E = 0.3
OMEGA_V = 0.2
LAMBDA_CRIT = 10.0

# Simulation configuration
N_VEHICLES = 50
SIM_DURATION_S = 600.0
WARMUP_S = 60.0
N_SEEDS = 5
SEEDS = [42, 123, 456, 789, 2024]
T_EXIT_MAX = 10.0  # normalisation bound for state vector
SPEED_MAX_MS = 33.3  # 120 km/h in m/s

# Speed distributions per scenario (calibrated from Roma taxi statistics)
SCENARIO_SPEEDS = {
    "morning_rush": {"mean": 11.0, "std": 4.0},  # congested ~40 km/h
    "off_peak": {"mean": 16.7, "std": 3.5},  # free ~60 km/h
    "evening_rush": {"mean": 9.0, "std": 3.5},  # heavy ~32 km/h
}

# System names
SYSTEMS = [
    "random",
    "greedy",
    "nsga2_static",
    "dqn_cold",
    "dqn_bc_only",
    "proposed",
]

SCENARIOS = ["morning_rush", "off_peak", "evening_rush"]
