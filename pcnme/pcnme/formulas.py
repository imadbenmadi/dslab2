"""
PCNME Mathematical Formulas
All formulas taken directly from methodology paper.
DO NOT MODIFY without updating paper.
"""

import math
import numpy as np
from .constants import (
    FOG_MIPS, CLOUD_MIPS, EC_THRESHOLD, P_TX, KAPPA, ALPHA,
    BANDWIDTH_MBPS, FOG_CLOUD_BW_MBPS, G5_LATENCY_MS, WAN_LATENCY_MS,
    E_REF, OMEGA_L, OMEGA_E, OMEGA_V, LAMBDA_CRIT
)

# ============================================================================
# EC CLASSIFICATION (Section 4)
# ============================================================================

def compute_ec(step_MI: int, fog_mips: int = FOG_MIPS) -> float:
    """
    EC(g_j) = l_j / mu_k   [seconds]
    
    Computes edge complexity of a step.
    Args:
        step_MI: computational load in Million Instructions
        fog_mips: fog node MIPS capacity
    
    Returns:
        edge complexity in seconds
    """
    return step_MI / fog_mips


def classify_step(step_MI: int, theta: float = EC_THRESHOLD) -> str:
    """
    Returns 'boulder' if EC >= theta, else 'pebble'.
    
    Classification is identical across all systems.
    Never change theta or fog_mips values.
    """
    return 'boulder' if compute_ec(step_MI) >= theta else 'pebble'


# ============================================================================
# EXECUTION TIME (Section 2)
# ============================================================================

def t_exec_fog(step_MI: int, fog_mips: int = FOG_MIPS, 
               fog_load: float = 0.0) -> float:
    """
    T_exec(g_j, f_k, t) = (l_j / (mu_k * (1 - rho_k(t)))) * 1000   [ms]
    
    Work-conserving processor sharing model on fog.
    
    Args:
        step_MI: computational load (MI)
        fog_mips: fog node capacity (MIPS)
        fog_load: current CPU utilization rho_k(t) in [0, 1)
    
    Returns:
        execution time in milliseconds
    
    Raises:
        AssertionError if fog_load >= 1.0
    """
    assert 0.0 <= fog_load < 1.0, f"Load must be in [0, 1), got {fog_load}"
    return (step_MI / (fog_mips * (1.0 - fog_load))) * 1000.0


def t_exec_cloud(step_MI: int, cloud_mips: int = CLOUD_MIPS) -> float:
    """
    T_exec(g_j, C) = (l_j / mu_c) * 1000   [ms]
    
    Execution time on cloud (no queueing model).
    """
    return (step_MI / cloud_mips) * 1000.0


# ============================================================================
# TRANSMISSION TIME (Section 2)
# ============================================================================

def t_tx_fog(data_KB: float, bandwidth_mbps: float = BANDWIDTH_MBPS,
             g5_latency_ms: float = G5_LATENCY_MS) -> float:
    """
    T_access(d) = (8*d / B) + delta_5G   [ms]
    
    Transmission time to fog node over 5G.
    
    Args:
        data_KB: data size in kilobytes
        bandwidth_mbps: 5G bandwidth (Mbps)
        g5_latency_ms: 5G link latency (ms)
    
    Returns:
        transmission time in milliseconds
    """
    return (8.0 * data_KB / bandwidth_mbps) + g5_latency_ms


def t_tx_cloud(data_KB: float, backbone_mbps: float = FOG_CLOUD_BW_MBPS,
               wan_latency_ms: float = WAN_LATENCY_MS) -> float:
    """
    T_tx_cloud(d) = (8*d / B_c) + delta_WAN   [ms]
    
    Transmission time to cloud over WAN backbone.
    """
    return (8.0 * data_KB / backbone_mbps) + wan_latency_ms


# ============================================================================
# TOTAL STEP LATENCY (Section 2)
# ============================================================================

def step_latency(step_MI: int, data_KB: float, destination: str,
                 fog_load: float = None) -> float:
    """
    L_j(x_j, t) = T_access(d_j_in) + T_exec(g_j, f_k, t)   if x_j in F
                  T_tx_cloud(d_j_in) + T_exec(g_j, C)       if x_j = C
    
    Computes total latency for a step.
    
    Args:
        step_MI: computational load
        data_KB: input data size
        destination: 'cloud' or fog node ID ('A', 'B', 'C', 'D')
        fog_load: fog node utilization (required if destination != 'cloud')
    
    Returns:
        total latency in milliseconds
    """
    if destination == 'cloud':
        return t_tx_cloud(data_KB) + t_exec_cloud(step_MI)
    else:
        assert fog_load is not None, "fog_load required for fog destination"
        return t_tx_fog(data_KB) + t_exec_fog(step_MI, FOG_MIPS, fog_load)


# ============================================================================
# ENERGY MODEL (Section 2)
# ============================================================================

def e_tx(data_KB: float, bandwidth_mbps: float = BANDWIDTH_MBPS) -> float:
    """
    E_tx(d) = P_tx * (8*d / (B * 1e3))   [Joules]
    
    Transmission energy for device to fog/cloud.
    
    Args:
        data_KB: data size in KB
        bandwidth_mbps: bandwidth in Mbps
    
    Returns:
        transmission energy in Joules
    """
    return P_TX * (8.0 * data_KB / (bandwidth_mbps * 1e3))


def step_energy(step_MI: int, data_KB: float, destination: str) -> float:
    """
    E_j(x_j) = E_tx(d_j_in) + E_comp(g_j)         if x_j in F
    E_j(x_j) = E_tx(d_j_in) + alpha * E_tx(d_j_in) if x_j = C
    
    Computes total energy consumption for a step.
    
    Args:
        step_MI: computational load
        data_KB: input data size
        destination: 'cloud' or fog node ID
    
    Returns:
        total energy in Joules
    """
    e_transmission = e_tx(data_KB)
    if destination == 'cloud':
        # Cloud: transmission + WAN penalty
        return e_transmission + ALPHA * e_transmission
    else:
        # Fog: transmission + local compute
        e_compute = KAPPA * step_MI
        return e_transmission + e_compute


# ============================================================================
# T_EXIT FORMULA (Section 7)
# ============================================================================

def compute_v_closing(vx: float, vy: float,
                      vehicle_x: float, vehicle_y: float,
                      fog_x: float, fog_y: float) -> float:
    """
    v_close = u_i(t) . n_hat_ik(t)
    
    Computes closing velocity (rate of vehicle leaving fog coverage).
    
    Args:
        vx, vy: vehicle velocity components (m/s)
        vehicle_x, vehicle_y: vehicle position
        fog_x, fog_y: fog node position
    
    Returns:
        closing velocity (m/s). Positive means vehicle is leaving fog zone.
    """
    dx = fog_x - vehicle_x
    dy = fog_y - vehicle_y
    dist = math.sqrt(dx**2 + dy**2)
    
    if dist < 1e-6:
        return 0.0
    
    # outward radial: negative of (fog - vehicle) / |fog - vehicle|
    nx = -dx / dist
    ny = -dy / dist
    return vx * nx + vy * ny


def compute_t_exit(vehicle_x: float, vehicle_y: float,
                   speed_ms: float, heading_deg: float,
                   fog_x: float, fog_y: float,
                   fog_radius: float = 250.0) -> float:
    """
    T_exit(v_i, f_k, t) = (R_k - ||q_i - p_k||) / v_close
                            if v_close > 0
                  T_exit = +inf           if v_close <= 0
    
    Computes time until vehicle leaves fog coverage.
    
    Args:
        vehicle_x, vehicle_y: vehicle position (metres)
        speed_ms: vehicle speed (m/s)
        heading_deg: vehicle heading (degrees)
        fog_x, fog_y: fog node position
        fog_radius: fog coverage radius (metres)
    
    Returns:
        time to exit (seconds). 0.0 if already outside, inf if moving away.
    """
    dist = math.sqrt((vehicle_x - fog_x)**2 + (vehicle_y - fog_y)**2)
    
    if dist >= fog_radius:
        return 0.0  # already outside zone
    
    heading_rad = math.radians(heading_deg)
    vx = speed_ms * math.cos(heading_rad)
    vy = speed_ms * math.sin(heading_rad)
    
    v_close = compute_v_closing(vx, vy, vehicle_x, vehicle_y, fog_x, fog_y)
    
    if v_close <= 0:
        return float('inf')  # not leaving coverage
    
    return (fog_radius - dist) / v_close


def select_handoff_mode(t_exec_ms: float, t_exit_s: float) -> str:
    """
    mode = DIRECT     if T_exec < T_exit
    mode = PROACTIVE  if T_exec >= T_exit
    
    Selects handoff mode based on execution vs exit times.
    
    Args:
        t_exec_ms: execution time (milliseconds)
        t_exit_s: time to exit (seconds)
    
    Returns:
        'direct' or 'proactive'
    """
    t_exec_s = t_exec_ms / 1000.0
    if t_exec_s < t_exit_s:
        return 'direct'
    return 'proactive'


# ============================================================================
# DQN STATE VECTOR (Section 6)
# ============================================================================

def build_state(fog_loads: dict, fog_queues: dict,
                step_MI: int, bw_util: float,
                vehicle_speed_ms: float, t_exit_s: float,
                deadline_remaining_ms: float,
                theta: float = EC_THRESHOLD,
                q_max: float = 50.0,
                t_exit_max: float = 10.0,
                speed_max: float = 33.3,
                deadline_ref: float = 200.0) -> list:
    """
    Builds 13-dimensional normalized state vector for DQN.
    
    s = (rho_A, rho_B, rho_C, rho_D,
         q_A/q_max, q_B/q_max, q_C/q_max, q_D/q_max,
         EC_hat, B_hat, speed_hat, T_exit_hat, deadline_hat)
    
    All dimensions in [0, 1].
    
    Args:
        fog_loads: dict of {'A': rho_A, 'B': rho_B, ...}
        fog_queues: dict of {'A': q_A, 'B': q_B, ...}
        step_MI: current step MI
        bw_util: bandwidth utilization [0, 1]
        vehicle_speed_ms: vehicle speed (m/s)
        t_exit_s: time to exit (seconds)
        deadline_remaining_ms: remaining deadline (ms)
        theta, q_max, t_exit_max, speed_max, deadline_ref: normalization bounds
    
    Returns:
        list of 13 normalized values in [0, 1]
    """
    ec = compute_ec(step_MI)
    ec_hat = min(ec / theta, 1.0)
    b_hat = min(bw_util, 1.0)
    s_hat = min(vehicle_speed_ms / speed_max, 1.0)
    te_hat = min(t_exit_s / t_exit_max, 1.0)
    dl_hat = min(deadline_remaining_ms / deadline_ref, 1.0)
    
    return [
        fog_loads['A'], fog_loads['B'], fog_loads['C'], fog_loads['D'],
        fog_queues['A'] / q_max, fog_queues['B'] / q_max,
        fog_queues['C'] / q_max, fog_queues['D'] / q_max,
        ec_hat, b_hat, s_hat, te_hat, dl_hat
    ]


# ============================================================================
# REWARD FUNCTION (Section 6)
# ============================================================================

def compute_reward(latency_ms: float, energy_j: float,
                   deadline_ms: float,
                   is_safety_critical: bool = False) -> float:
    """
    R(g_j, x_j) = -omega_L * L_tilde
                  - omega_E * E_tilde
                  - omega_V * 1[L_j > d_j_local] * lambda
    
    Computes reward signal for DQN training.
    
    Args:
        latency_ms: step latency (ms)
        energy_j: step energy (J)
        deadline_ms: step deadline (ms)
        is_safety_critical: whether step is safety-critical
    
    Returns:
        reward value (negative)
    """
    L_tilde = min(latency_ms / deadline_ms, 3.0)
    E_tilde = min(energy_j / E_REF, 3.0)
    violation = 1.0 if latency_ms > deadline_ms else 0.0
    lam = LAMBDA_CRIT if is_safety_critical else 1.0
    
    return -(OMEGA_L * L_tilde
             + OMEGA_E * E_tilde
             + OMEGA_V * violation * lam)


# ============================================================================
# TD TARGET AND LOSS (Section 6)
# ============================================================================

def td_target(reward, next_q_values, done, gamma=0.95):
    """
    y_t = r_t + gamma * max_a' Q(s_{t+1}, a'; theta^-) * (1 - done)
    
    Computes TD target for Bellman backup.
    
    Args:
        reward: immediate reward (batch)
        next_q_values: Q-values for next state (batch x actions)
        done: episode termination flags (batch)
        gamma: discount factor
    
    Returns:
        TD target values (batch)
    """
    import torch
    return reward + gamma * next_q_values.max(dim=1)[0] * (1.0 - done)


def huber_loss(predicted_q, target_q, delta=1.0):
    """
    H_delta(y - Q(s,a;theta))
    
    Computes Huber loss for robustness to outliers.
    """
    import torch.nn.functional as F
    return F.huber_loss(predicted_q, target_q, delta=delta, reduction='mean')


# ============================================================================
# BEHAVIORAL CLONING LOSS (Section 6)
# ============================================================================

def bc_loss(q_values, target_actions):
    """
    L_BC(theta) = -(1/|D_BC|) * sum log softmax(Q(s,a*;theta))
    
    Standard cross-entropy between Q-values and NSGA-II optimal actions.
    
    Args:
        q_values: predicted Q-values (batch x actions)
        target_actions: NSGA-II optimal actions (batch)
    
    Returns:
        cross-entropy loss
    """
    import torch.nn.functional as F
    return F.cross_entropy(q_values, target_actions)


# ============================================================================
# EVALUATION METRICS (Section 10)
# ============================================================================

def feasibility_rate(latencies_ms, deadlines_ms):
    """
    (1/|T|) * sum 1[L_tau <= D_tau]
    
    Fraction of tasks meeting deadline.
    """
    met = [l <= d for l, d in zip(latencies_ms, deadlines_ms)]
    return float(np.mean(met))


def avg_latency(latencies_ms):
    """Mean latency across tasks."""
    return float(np.mean(latencies_ms))


def avg_energy(energies_j):
    """Mean energy across tasks."""
    return float(np.mean(energies_j))


def handoff_success_rate(handoff_results: list):
    """
    Fraction of handoff events with no task re-submission.
    
    Args:
        handoff_results: list of boolean success flags
    
    Returns:
        success rate or None if no handoffs
    """
    if not handoff_results:
        return None
    return float(np.mean(handoff_results))


def fog_utilisation_balance(fog_load_history: dict):
    """
    Std of mean CPU utilisation across fog nodes.
    Lower = more balanced load.
    
    Args:
        fog_load_history: dict of node ID -> list of loads
    
    Returns:
        standard deviation of mean loads
    """
    means = [np.mean(loads) for loads in fog_load_history.values()]
    return float(np.std(means))


def bootstrap_ci(data, stat_fn=np.mean, n_boot=10000, ci=0.95):
    """
    Compute 95% bootstrap confidence interval.
    
    Args:
        data: array of values
        stat_fn: statistic function (default: mean)
        n_boot: number of bootstrap samples
        ci: confidence interval (e.g., 0.95 for 95%)
    
    Returns:
        tuple (point_estimate, lower_ci, upper_ci)
    """
    data = np.array(data)
    boot = [stat_fn(np.random.choice(data, len(data), replace=True))
            for _ in range(n_boot)]
    alpha = (1 - ci) / 2
    return (
        stat_fn(data),
        np.percentile(boot, alpha * 100),
        np.percentile(boot, (1 - alpha) * 100)
    )


def wilcoxon_test(system_a_results, system_b_results):
    """
    Wilcoxon signed-rank test.
    
    Args:
        system_a_results: results from system A
        system_b_results: results from system B
    
    Returns:
        (statistic, p_value) where p < 0.05 means significant improvement
    """
    from scipy import stats
    stat, p = stats.wilcoxon(system_a_results, system_b_results,
                              alternative='less')
    return stat, p
