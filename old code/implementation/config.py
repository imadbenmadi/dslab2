from settings.env_loader import (
    get_env_bool,
    get_env_float,
    get_env_int,
    get_env_list_int,
    load_dotenv,
)

load_dotenv()

# System parameters
FOG_MIPS        = get_env_int("FOG_MIPS", 2000)               # MIPS per fog node
CLOUD_MIPS      = get_env_int("CLOUD_MIPS", 8000)             # Cloud has 4x compute
EC_THRESHOLD    = get_env_float("EC_THRESHOLD", 1.0)          # Task sends to cloud if > 1 second
BANDWIDTH_MBPS  = get_env_float("BANDWIDTH_MBPS", 100)        # IoT to fog bandwidth
FOG_CLOUD_BW    = get_env_float("FOG_CLOUD_BW", 1000)         # Backbone link
FOG_FOG_BW      = get_env_float("FOG_FOG_BW", 100)            # Inter-fog WiFi
WAN_LATENCY_MS  = get_env_float("WAN_LATENCY_MS", 30)         # Cloud round-trip
G5_LATENCY_MS   = get_env_float("G5_LATENCY_MS", 2)           # Vehicle to fog

# Istanbul city topology
# 1000m x 1000m covering Besiktas, Sisli, Kadikoy, Uskudar
FOG_NODES = {
    'A': {'pos': (200, 500), 'name': 'Besiktas',  'load': 0.30},
    'B': {'pos': (500, 200), 'name': 'Sisli',     'load': 0.45},
    'C': {'pos': (800, 500), 'name': 'Kadikoy',   'load': 0.35},
    'D': {'pos': (500, 800), 'name': 'Uskudar',   'load': 0.40},
}
FOG_COVERAGE_RADIUS = get_env_float("FOG_COVERAGE_RADIUS", 250)  # Coverage radius in meters
Q_MAX = get_env_int("Q_MAX", 50)                                  # Queue limit before triggering cloud offload

# Vehicle mobility settings
N_VEHICLES         = get_env_int("N_VEHICLES", 50)            # Vehicles in simulation
VEHICLE_SPEED_MEAN = get_env_float("VEHICLE_SPEED_MEAN", 60)  # Average speed km/h
VEHICLE_SPEED_STD  = get_env_float("VEHICLE_SPEED_STD", 15)   # Speed variation
TASK_RATE_HZ       = get_env_float("TASK_RATE_HZ", 10)        # Camera frame rate

# Object detection pipeline structure
# YOLOv5 workflow: capture -> preprocess -> inference -> classify -> alert
DAG_STEPS = {
    1: {'MI': 20,   'in_KB': 8192, 'out_KB': 200,  'name': 'Capture+Compress', 'runs_on': 'device'},
    2: {'MI': 200,  'in_KB': 200,  'out_KB': 50,   'name': 'Pre-process',      'deadline_ms': 30},
    3: {'MI': 2000, 'in_KB': 50,   'out_KB': 30,   'name': 'Feature Extract',  'deadline_ms': 80},
    4: {'MI': 8000, 'in_KB': 30,   'out_KB': 5,    'name': 'Object Classify',  'deadline_ms': 150},
    5: {'MI': 50,   'in_KB': 5,    'out_KB': 1,    'name': 'Alert Generate',   'deadline_ms': 200},
}
TOTAL_DEADLINE_MS = get_env_float("TOTAL_DEADLINE_MS", 200)   # End-to-end requirement

# Optimization parameters
NSGA_POP_SIZE   = get_env_int("NSGA_POP_SIZE", 50)            # Population size
NSGA_GENS       = get_env_int("NSGA_GENS", 50)                # Generations
MMDE_F          = get_env_float("MMDE_F", 0.5)                # Mutation scaling
MMDE_CR         = get_env_float("MMDE_CR", 0.9)               # Crossover probability
NSGA_BATCH_SIZE = get_env_int("NSGA_BATCH_SIZE", 100)         # Tasks per batch
N_OFFLINE_BATCHES = get_env_int("N_OFFLINE_BATCHES", 1000)    # Historical data for training

# Agent 1: Task placement
AGENT1_STATE_DIM   = 13
AGENT1_ACTION_DIM  = 5      # Fog A, B, C, D, Cloud
AGENT1_HIDDEN      = get_env_list_int("AGENT1_HIDDEN", [256, 128])
AGENT1_LR          = get_env_float("AGENT1_LR", 0.001)
AGENT1_GAMMA       = get_env_float("AGENT1_GAMMA", 0.95)
AGENT1_EPSILON_START = get_env_float("AGENT1_EPSILON_START", 0.30)
AGENT1_EPSILON_END   = get_env_float("AGENT1_EPSILON_END", 0.05)
AGENT1_EPSILON_DECAY = get_env_int("AGENT1_EPSILON_DECAY", 10000)  # steps
AGENT1_BATCH_SIZE  = get_env_int("AGENT1_BATCH_SIZE", 64)
AGENT1_BUFFER_SIZE = get_env_int("AGENT1_BUFFER_SIZE", 50000)
AGENT1_TARGET_UPDATE = get_env_int("AGENT1_TARGET_UPDATE", 1000)    # steps
AGENT1_REWARD_WEIGHTS = {'latency': 0.5, 'energy': 0.3, 'violation': 0.2}
AGENT1_DEADLINE_PENALTY = get_env_float("AGENT1_DEADLINE_PENALTY", 10.0)  # multiplier for missing deadline

# ── DQN Agent 2 (SDN routing) ────────────────────────────────────────────────
AGENT2_STATE_DIM   = 15
AGENT2_ACTION_DIM  = 5      # primary, alt1, alt2, VIP_reserve, best_effort
AGENT2_HIDDEN      = get_env_list_int("AGENT2_HIDDEN", [256, 128])
AGENT2_LR          = get_env_float("AGENT2_LR", 0.001)
AGENT2_GAMMA       = get_env_float("AGENT2_GAMMA", 0.95)
AGENT2_EPSILON_START = get_env_float("AGENT2_EPSILON_START", 0.25)
AGENT2_EPSILON_END   = get_env_float("AGENT2_EPSILON_END", 0.05)
AGENT2_EPSILON_DECAY = get_env_int("AGENT2_EPSILON_DECAY", 8000)
AGENT2_BATCH_SIZE  = get_env_int("AGENT2_BATCH_SIZE", 64)
AGENT2_BUFFER_SIZE = get_env_int("AGENT2_BUFFER_SIZE", 50000)
AGENT2_TARGET_UPDATE = get_env_int("AGENT2_TARGET_UPDATE", 1000)
AGENT2_REWARD_WEIGHTS = {'delivery': 0.5, 'delay': 0.3, 'overhead': 0.2}
AGENT2_PACKET_DROP_PENALTY = get_env_float("AGENT2_PACKET_DROP_PENALTY", 50.0)
AGENT2_PREINSTALL_BONUS    = get_env_float("AGENT2_PREINSTALL_BONUS", 0.3)

# ── Simulation runtime ────────────────────────────────────────────────────────
SIM_DURATION_S  = get_env_float("SIM_DURATION_S", 600)   # 10 minutes
WARMUP_S        = get_env_float("WARMUP_S", 60)          # excluded from results
RANDOM_SEED     = get_env_int("RANDOM_SEED", 42)
N_RUNS          = get_env_int("N_RUNS", 5)               # independent runs for statistical validity

# ── Bootstrap pretraining runtime guards ─────────────────────────────────────
ENABLE_BOOTSTRAP_PRETRAIN = get_env_bool("ENABLE_BOOTSTRAP_PRETRAIN", True)
BOOTSTRAP_TASKS = get_env_int("BOOTSTRAP_TASKS", 8)               # Number of synthetic boot DAGs at startup
BOOTSTRAP_NSGA_POP_SIZE = get_env_int("BOOTSTRAP_NSGA_POP_SIZE", 20)  # Smaller than full offline optimization for fast startup
BOOTSTRAP_NSGA_GENS = get_env_int("BOOTSTRAP_NSGA_GENS", 10)
BOOTSTRAP_MAX_SECONDS = get_env_float("BOOTSTRAP_MAX_SECONDS", 12.0)  # Safety cap to avoid blocking app launch
