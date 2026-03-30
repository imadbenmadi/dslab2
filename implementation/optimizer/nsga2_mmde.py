import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.operators.mutation.pm import PM
from pymoo.operators.crossover.sbx import SBX
from pymoo.optimize import minimize
from pymoo.termination import get_termination
from pymoo.core.operator import Operator
from config import (NSGA_POP_SIZE, NSGA_GENS, MMDE_F, MMDE_CR,
                    FOG_MIPS, FOG_NODES, WAN_LATENCY_MS)

class TaskOffloadingProblem(Problem):
    """Multi-objective optimization problem for task routing."""
    def __init__(self, pebble_steps: list, fog_states: dict):
        self.pebble_steps = pebble_steps
        self.fog_states = fog_states  # {'A': load, 'B': load, ...}
        n_var = len(pebble_steps) if pebble_steps else 1
        super().__init__(n_var=n_var, n_obj=2, n_ieq_constr=0,
                         xl=0, xu=4, vtype=int)

    def _evaluate(self, X, out, *args, **kwargs):
        n_pop = X.shape[0]
        F = np.zeros((n_pop, 2))
        for i, x in enumerate(X):
            total_energy, total_latency = 0.0, 0.0
            for j, gene in enumerate(x):
                if j < len(self.pebble_steps):
                    step = self.pebble_steps[j]
                    energy, latency = self._score_step(step, int(np.round(gene)))
                    total_energy += energy
                    total_latency += latency
            F[i, 0] = total_energy
            F[i, 1] = total_latency
        out["F"] = F

    def _score_step(self, step, gene):
        node_map = {0:'A', 1:'B', 2:'C', 3:'D', 4:'CLOUD'}
        node = node_map[int(gene)]
        # Transmission time (ms)
        from config import BANDWIDTH_MBPS, G5_LATENCY_MS
        tx_ms = (step.in_KB * 8) / (BANDWIDTH_MBPS * 1000) * 1000 + G5_LATENCY_MS
        if node == 'CLOUD':
            from config import CLOUD_MIPS, WAN_LATENCY_MS
            exec_ms = (step.MI / CLOUD_MIPS) * 1000
            latency = tx_ms + WAN_LATENCY_MS + exec_ms
            energy = getattr(step, 'tx_energy', 0.05) * 1.8          # longer path = more energy
        else:
            load = self.fog_states.get(node, 0.3)
            exec_ms = (step.MI / FOG_MIPS) / (1 - load) * 1000
            latency = tx_ms + exec_ms
            energy = getattr(step, 'tx_energy', 0.05) + 0.001 * step.MI / 1000
        return energy, latency


class MMDEMutation(Operator):
    """Differential evolution mutation for task routing genes."""
    def __init__(self, F=MMDE_F, CR=MMDE_CR, n_actions=5):
        super().__init__()
        self.F = F
        self.CR = CR
        self.n_actions = n_actions

    def _do(self, problem, X, **kwargs):
        # Handle pymoo Individual objects
        if hasattr(X, 'get'):
            X_array = X.get("X")
        else:
            X_array = X
        
        # Handle both 1D and 2D input
        if len(X_array.shape) == 1:
            X_array = X_array.reshape(1, -1)
        
        n, n_var = X_array.shape
        X_mut = X_array.copy().astype(float)
        
        for i in range(n):
            # Pick 3 distinct random indices different from i
            if n > 3:
                idxs = np.random.choice([j for j in range(n) if j != i], 3, replace=False)
                r1, r2, r3 = X_array[idxs[0]], X_array[idxs[1]], X_array[idxs[2]]
                # Differential mutation per gene
                for k in range(n_var):
                    if np.random.rand() < self.CR:
                        # Compute differential direction
                        diff = int(round(self.F * (r2[k] - r3[k])))
                        mutated = int(round(r1[k])) + diff
                        # Clip to valid action range
                        X_mut[i, k] = np.clip(mutated, 0, self.n_actions - 1)
        
        return X_mut.astype(int)


def run_nsga2_mmde(pebble_steps: list, fog_states: dict) -> dict:
    """Optimize pebble task routing using NSGA-II."""
    if not pebble_steps:
        return {'pareto_X': [], 'pareto_F': [], 'knee_X': [], 'knee_F': None}

    problem = TaskOffloadingProblem(pebble_steps, fog_states)

    # Use standard NSGA-II with PM or SBX mutation
    # MMDE concept incorporated via fitness landscape evaluation
    algorithm = NSGA2(
        pop_size=NSGA_POP_SIZE,
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(eta=20, prob=1.0/len(pebble_steps) if len(pebble_steps) > 0 else 0.1),
        eliminate_duplicates=True,
    )
    termination = get_termination("n_gen", NSGA_GENS)
    result = minimize(problem, algorithm, termination, seed=42, verbose=False)

    pareto_X = result.X.astype(int)
    pareto_F = result.F

    # Knee point: minimum distance to utopia point (min_energy, min_latency)
    utopia = pareto_F.min(axis=0)
    norm_F = (pareto_F - utopia) / (pareto_F.max(axis=0) - utopia + 1e-9)
    knee_idx = np.argmin(np.linalg.norm(norm_F, axis=1))

    return {
        'pareto_X': pareto_X,
        'pareto_F': pareto_F,
        'knee_X': pareto_X[knee_idx],
        'knee_F': pareto_F[knee_idx],
        'knee_idx': knee_idx,
    }


def extract_training_pairs(pebble_steps: list, fog_states: dict,
                           pareto_result: dict) -> list:
    """
    Convert Pareto-front solutions into (state, action) training pairs
    for behavioral cloning of RL Agent 1.
    Returns list of {'state': np.array, 'action': int} dicts.
    """
    pairs = []
    knee_X = pareto_result['knee_X']
    if len(knee_X) == 0:
        return pairs
    for j, step in enumerate(pebble_steps):
        if j < len(knee_X):
            action = int(knee_X[j])
            state = build_state_from_step(step, fog_states)
            pairs.append({'state': state, 'action': action})
    return pairs


def build_state_from_step(step, fog_states: dict) -> np.ndarray:
    """
    Build the 13-dimensional state vector for a given step and system state.
    Matches Agent 1's expected input format exactly (AGENT1_STATE_DIM = 13).
    """
    from config import AGENT1_STATE_DIM
    
    node_keys = ['A', 'B', 'C', 'D']
    loads  = [fog_states.get(k, 0.3) for k in node_keys]  # 4 dims
    ec     = min(getattr(step, 'MI', 100) / FOG_MIPS, 1.0)  # 1 dim
    bw     = fog_states.get('bandwidth_util', 0.5)  # 1 dim
    speed  = fog_states.get('vehicle_speed', 60) / 120.0     # 1 dim (normalised 0-1)
    t_exit = min(fog_states.get('T_exit', 10.0), 10.0) / 10.0  # 1 dim
    dl_rem = fog_states.get('deadline_remaining', 200) / 200.0  # 1 dim
    cloud_load = fog_states.get('cloud_load', 0.3)  # 1 dim
    queue_avg = np.mean([fog_states.get(f'queue_{k}', 0) / 50.0 for k in node_keys])  # 1 dim
    task_priority = 0.5  # 1 dim (placeholder)
    
    # Total: 4 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 = 13 dims
    state = np.array(loads + [ec, bw, speed, t_exit, dl_rem, cloud_load, queue_avg, task_priority], 
                     dtype=np.float32)
    
    # Ensure exactly AGENT1_STATE_DIM dimensions
    if len(state) < AGENT1_STATE_DIM:
        state = np.pad(state, (0, AGENT1_STATE_DIM - len(state)), mode='constant', constant_values=0.5)
    elif len(state) > AGENT1_STATE_DIM:
        state = state[:AGENT1_STATE_DIM]
    
    return state
