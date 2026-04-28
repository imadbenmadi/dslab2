"""
All mathematical formulas from the PCNME methodology paper.
Every formula is taken verbatim from the paper sections.
"""

import math
import numpy as np
import torch
import torch.nn.functional as F
from scipy import stats

from .constants import (
    FOG_MIPS, CLOUD_MIPS, EC_THRESHOLD,
    BANDWIDTH_MBPS, FOG_CLOUD_BW_MBPS, G5_LATENCY_MS, WAN_LATENCY_MS,
    P_TX, KAPPA, ALPHA, E_REF,
    OMEGA_L, OMEGA_E, OMEGA_V, LAMBDA_CRIT,
    DAG, STATE_DIM, T_EXIT_MAX, SPEED_MAX_MS
)


# ============================================================================
# EC CLASSIFICATION (Section 4 of methodology)
# ============================================================================

def compute_ec(step_MI: int, fog_mips: int = FOG_MIPS) -> float:
    """EC(g_j) = l_j / mu_k   [seconds]"""
    return step_MI / fog_mips


def classify_step(step_MI: int, theta: float = EC_THRESHOLD) -> str:
    """Returns 'boulder' if EC >= theta, else 'pebble'."""
    return "boulder" if compute_ec(step_MI) >= theta else "pebble"


# ============================================================================
# EXECUTION TIME (Section 2 of methodology)
# ============================================================================

def t_exec_fog(step_MI: int, fog_mips: int = FOG_MIPS, fog_load: float = 0.0) -> float:
    """
    T_exec(g_j, f_k, t) = (l_j / (mu_k * (1 - rho_k(t)))) * 1000   [ms]
    Work-conserving processor sharing model.
    """
    assert 0.0 <= fog_load < 1.0, f"Load must be in [0, 1), got {fog_load}"
    return (step_MI / (fog_mips * (1.0 - fog_load))) * 1000.0


def t_exec_cloud(step_MI: int, cloud_mips: int = CLOUD_MIPS) -> float:
    """T_exec(g_j, C) = (l_j / mu_c) * 1000   [ms]"""
    return (step_MI / cloud_mips) * 1000.0


# ============================================================================
# TRANSMISSION TIME (Section 2 of methodology)
# ============================================================================

def t_tx_fog(data_KB: float, bandwidth_mbps: float = BANDWIDTH_MBPS,
             g5_latency_ms: float = G5_LATENCY_MS) -> float:
    """T_access(d) = (8*d / B) + delta_5G   [ms]"""
    return (8.0 * data_KB / bandwidth_mbps) + g5_latency_ms


def t_tx_cloud(data_KB: float, backbone_mbps: float = FOG_CLOUD_BW_MBPS,
               wan_latency_ms: float = WAN_LATENCY_MS) -> float:
    """T_tx_cloud(d) = (8*d / B_c) + delta_WAN   [ms]"""
    return (8.0 * data_KB / backbone_mbps) + wan_latency_ms


# ============================================================================
# TOTAL STEP LATENCY (Section 2 of methodology)
# ============================================================================

def step_latency(step_MI: int, data_KB: float, destination: str,
                 fog_load: float = 0.0) -> float:
    """
    L_j(x_j, t) =
        T_access(d_j_in) + T_exec(g_j, f_k, t)   if x_j in F
        T_tx_cloud(d_j_in) + T_exec(g_j, C)       if x_j = C
    """
    if destination == "cloud":
        return t_tx_cloud(data_KB) + t_exec_cloud(step_MI)
    else:
        return t_tx_fog(data_KB) + t_exec_fog(step_MI, FOG_MIPS, fog_load)


# ============================================================================
# ENERGY (Section 2 of methodology)
# ============================================================================

def e_tx(data_KB: float, bandwidth_mbps: float = BANDWIDTH_MBPS) -> float:
    """E_tx(d) = P_tx * (8*d / (B * 1e3))   [Joules]"""
    return P_TX * (8.0 * data_KB / (bandwidth_mbps * 1e3))


def step_energy(step_MI: int, data_KB: float, destination: str) -> float:
    """
    E_j(x_j) = E_tx(d_j_in) + E_comp(g_j)         if x_j in F
    E_j(x_j) = E_tx(d_j_in) + alpha * E_tx(d_j_in) if x_j = C
    """
    e_transmission = e_tx(data_KB)
    if destination == "cloud":
        return e_transmission + ALPHA * e_transmission
    else:
        e_compute = KAPPA * step_MI
        return e_transmission + e_compute


# ============================================================================
# T_EXIT FORMULA (Section 7 of methodology)
# ============================================================================

def compute_v_closing(vx: float, vy: float,
                      vehicle_x: float, vehicle_y: float,
                      fog_x: float, fog_y: float) -> float:
    """
    v_close = u_i(t) . n_hat_ik(t)
    n_hat_ik = outward radial unit vector from fog centre toward vehicle
    """
    dx = fog_x - vehicle_x
    dy = fog_y - vehicle_y
    dist = math.sqrt(dx**2 + dy**2)
    if dist < 1e-6:
        return 0.0
    # outward radial: negative of (fog - vehicle) / |fog - vehicle|
    nx, ny = -dx / dist, -dy / dist
    return vx * nx + vy * ny


def compute_t_exit(vehicle_x: float, vehicle_y: float,
                   speed_ms: float, heading_deg: float,
                   fog_x: float, fog_y: float,
                   fog_radius: float = 250.0) -> float:
    """
    T_exit(v_i, f_k, t) = (R_k - ||q_i - p_k||) / v_close
                            if v_close > 0
    T_exit = +inf           if v_close <= 0
    """
    dist = math.sqrt((vehicle_x - fog_x)**2 + (vehicle_y - fog_y)**2)
    if dist >= fog_radius:
        return 0.0  # already outside zone
    heading_rad = math.radians(heading_deg)
    vx = speed_ms * math.cos(heading_rad)
    vy = speed_ms * math.sin(heading_rad)
    v_close = compute_v_closing(vx, vy, vehicle_x, vehicle_y, fog_x, fog_y)
    if v_close <= 0:
        return float("inf")
    return (fog_radius - dist) / v_close


def select_handoff_mode(t_exec_ms: float, t_exit_s: float) -> str:
    """
    mode = DIRECT     if T_exec < T_exit
    mode = PROACTIVE  if T_exec >= T_exit
    T_exec is in ms, T_exit is in seconds — convert before comparing.
    """
    t_exec_s = t_exec_ms / 1000.0
    if t_exec_s < t_exit_s:
        return "direct"
    return "proactive"


# ============================================================================
# DQN STATE VECTOR (Section 6 of methodology)
# ============================================================================

def build_state(fog_loads: dict, fog_queues: dict,
                step_MI: int,
                vehicle_speed_ms: float, t_exit_s: float,
                theta: float = EC_THRESHOLD,
                q_max: float = 50.0,
                t_exit_max: float = T_EXIT_MAX,
                speed_max: float = SPEED_MAX_MS) -> list:
    """
    Build 11-dimensional state vector per methodology Eq. (21):
    s = (rho_A, rho_B, rho_C, rho_D,
         q_A/q_max, q_B/q_max, q_C/q_max, q_D/q_max,
         EC_hat, speed_hat, T_exit_hat)
    
    Removed: B_hat (network is static), deadline_hat (captured in T_exit).
    All components normalized to [0, 1].
    """
    ec = compute_ec(step_MI)
    ec_hat = min(ec / theta, 1.0)
    s_hat = min(vehicle_speed_ms / speed_max, 1.0)
    te_hat = min(t_exit_s / t_exit_max, 1.0)
    return [
        fog_loads.get("A", 0.0),
        fog_loads.get("B", 0.0),
        fog_loads.get("C", 0.0),
        fog_loads.get("D", 0.0),
        fog_queues.get("A", 0) / q_max,
        fog_queues.get("B", 0) / q_max,
        fog_queues.get("C", 0) / q_max,
        fog_queues.get("D", 0) / q_max,
        ec_hat,
        s_hat,
        te_hat,
    ]


# ============================================================================
# REWARD FUNCTION (Section 6 of methodology)
# ============================================================================

def compute_reward(latency_ms: float, energy_j: float,
                   deadline_ms: float,
                   is_safety_critical: bool = False) -> float:
    """
    R(g_j, x_j) = -omega_L * L_tilde
                  - omega_E * E_tilde
                  - omega_V * 1[L_j > d_j_local] * lambda
    omega_L = 0.5, omega_E = 0.3, omega_V = 0.2
    lambda = 10.0 for safety-critical steps, 1.0 otherwise
    """
    L_tilde = min(latency_ms / deadline_ms, 3.0)
    E_tilde = min(energy_j / E_REF, 3.0)
    violation = 1.0 if latency_ms > deadline_ms else 0.0
    lam = LAMBDA_CRIT if is_safety_critical else 1.0

    return -(OMEGA_L * L_tilde
             + OMEGA_E * E_tilde
             + OMEGA_V * violation * lam)


# ============================================================================
# LOSS FUNCTIONS (Section 6 of methodology)
# ============================================================================

def td_target(reward, next_q_values, done, gamma=0.95):
    """y_t = r_t + gamma * max_a' Q(s_{t+1}, a'; theta^-) * (1 - done)"""
    return reward + gamma * next_q_values.max(dim=1)[0] * (1.0 - done)


def huber_loss(predicted_q, target_q, delta=1.0):
    """Huber loss H_delta(y - Q(s,a;theta))"""
    return F.huber_loss(predicted_q, target_q, delta=delta, reduction="mean")


def bc_loss(q_values, target_actions):
    """
    L_BC(theta) = -(1/|D_BC|) * sum log softmax(Q(s,a*;theta))
    Standard cross-entropy between Q-values and NSGA-II optimal actions.
    """
    return F.cross_entropy(q_values, target_actions)


# ============================================================================
# EVALUATION METRICS (Section 10 of methodology)
# ============================================================================

def feasibility_rate(latencies_ms, deadlines_ms):
    """(1/|T|) * sum 1[L_tau <= D_tau]"""
    met = [l <= d for l, d in zip(latencies_ms, deadlines_ms)]
    return np.mean(met) if met else 0.0


def avg_latency(latencies_ms):
    """Average latency across all tasks."""
    return np.mean(latencies_ms) if latencies_ms else 0.0


def avg_energy(energies_j):
    """Average energy across all tasks."""
    return np.mean(energies_j) if energies_j else 0.0


def handoff_success_rate(handoff_results: list):
    """Fraction of handoff events with no task re-submission."""
    if not handoff_results:
        return None
    return np.mean(handoff_results)


def bootstrap_ci(data, stat_fn=np.mean, n_boot=10000, ci=0.95):
    """95% bootstrap confidence interval."""
    data = np.array(data)
    if len(data) == 0:
        return (0.0, 0.0, 0.0)
    boot = [stat_fn(np.random.choice(data, len(data), replace=True))
            for _ in range(n_boot)]
    alpha = (1 - ci) / 2
    return (stat_fn(data),
            np.percentile(boot, alpha * 100),
            np.percentile(boot, (1 - alpha) * 100))


def wilcoxon_test(system_a_results, system_b_results):
    """
    Wilcoxon signed-rank test.
    Returns (statistic, p_value).
    p < 0.05 means improvement is statistically significant.
    """
    stat, p = stats.wilcoxon(system_a_results, system_b_results,
                              alternative="less")
    return stat, p
