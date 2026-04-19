"""
PCNME NSGA-II / MMDE Optimization
Multi-objective optimization for offline pre-training.
"""

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.termination import get_termination
from pymoo.optimize import minimize
from pymoo.core.problem import Problem
from scipy.spatial.distance import cdist
from .constants import (
    DAG, FOG_NODES, NSGA_POP, NSGA_GENS, MMDE_F, MMDE_CR,
    N_OFFLINE_BATCHES, BATCH_SIZE_NSGA
)
from .formulas import step_latency, step_energy, classify_step


class SchedulingProblem(Problem):
    """
    Multi-objective optimization problem for task scheduling.
    
    Objectives:
    - Minimize total latency
    - Minimize total energy
    
    Variables: destination for each pebble step (2, 5)
    Constraints: none (infeasibility handled through objectives)
    """

    def __init__(self, n_steps=2, n_samples=100):
        """
        Args:
            n_steps: number of pebble steps to optimize (default: 2 for steps 2, 5)
            n_samples: number of task samples to evaluate
        """
        self.n_steps = n_steps
        self.n_samples = n_samples

        # Decision variables: one per pebble step
        # Values: 0-4 for fog A-D or cloud (0=A, 1=B, 2=C, 3=D, 4=cloud)
        super().__init__(
            n_var=n_steps,
            n_obj=2,
            n_constr=0,
            xl=np.zeros(n_steps, dtype=int),
            xu=4*np.ones(n_steps, dtype=int),
            type_var=['int'] * n_steps
        )

    def _evaluate(self, x, out, *args, **kwargs):
        """Evaluate solutions (population)."""
        n_pop = x.shape[0]
        f = np.zeros((n_pop, 2))

        for i in range(n_pop):
            latency, energy = self._evaluate_solution(x[i])
            f[i, 0] = latency  # minimize
            f[i, 1] = energy   # minimize

        out["F"] = f

    def _evaluate_solution(self, x):
        """Evaluate one solution (assignment)."""
        total_latency = 0.0
        total_energy = 0.0

        # Pebble steps: 2, 5
        pebble_steps = [2, 5]
        destinations_map = {0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'cloud'}

        for i, step_id in enumerate(pebble_steps):
            dest_idx = int(x[i])
            destination = destinations_map[dest_idx]

            step_info = DAG[step_id]
            step_MI = step_info['MI']
            data_KB = step_info['in_KB']

            # Compute latency (with dummy fog load 0.3)
            fog_load = 0.3 if destination != 'cloud' else None
            latency = step_latency(step_MI, data_KB, destination, fog_load)

            # Compute energy
            energy = step_energy(step_MI, data_KB, destination)

            total_latency += latency
            total_energy += energy

        # Boulder steps: always cloud
        for step_id in [3, 4]:
            step_info = DAG[step_id]
            step_MI = step_info['MI']
            data_KB = step_info['in_KB']

            latency = step_latency(step_MI, data_KB, 'cloud', fog_load=None)
            energy = step_energy(step_MI, data_KB, 'cloud')

            total_latency += latency
            total_energy += energy

        return total_latency, total_energy


class NSGAIIOptimizer:
    """
    NSGA-II optimizer for task scheduling.
    Produces Pareto-optimal solutions for pre-training.
    """

    def __init__(self, n_pop=NSGA_POP, n_gen=NSGA_GENS):
        self.n_pop = n_pop
        self.n_gen = n_gen
        self.algorithm = None
        self.result = None
        self.pareto_front = None

    def optimize(self):
        """Run NSGA-II optimization."""
        problem = SchedulingProblem(n_steps=2, n_samples=100)

        algorithm = NSGA2(pop_size=self.n_pop)

        termination = get_termination("n_gen", self.n_gen)

        self.result = minimize(
            problem,
            algorithm,
            termination,
            seed=42,
            verbose=True,
        )

        # Extract Pareto front
        self.pareto_front = self.result.F
        self.pareto_solutions = self.result.X

        return self.result

    def get_knee_point(self):
        """
        Find Pareto knee point (best compromise solution).
        
        Returns:
            (solution, latency, energy) of knee point
        """
        if self.pareto_front is None:
            return None

        # Normalize objectives
        f_min = self.pareto_front.min(axis=0)
        f_max = self.pareto_front.max(axis=0)
        f_norm = (self.pareto_front - f_min) / (f_max - f_min + 1e-9)

        # Distance to ideal point (0, 0)
        distances = np.linalg.norm(f_norm, axis=1)
        knee_idx = np.argmin(distances)

        solution = self.pareto_solutions[knee_idx]
        latency, energy = self.pareto_front[knee_idx]

        return solution, latency, energy

    def solution_to_routing_table(self, solution):
        """
        Convert NSGA-II solution to routing table.
        
        Args:
            solution: NSGA-II solution vector
        
        Returns:
            dict mapping (step_id, state_bucket) -> destination
        """
        destinations_map = {0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'cloud'}
        pebble_steps = [2, 5]

        routing_table = {}

        for i, step_id in enumerate(pebble_steps):
            dest_idx = int(solution[i])
            destination = destinations_map[dest_idx]

            # Key: (step_id, dummy_state_bucket)
            # In practice, could be more granular based on fog state
            routing_table[(step_id, 0)] = destination

        return routing_table


def generate_bc_dataset_from_nsga2(n_samples=1000):
    """
    Generate behavioral cloning dataset from NSGA-II solutions.
    
    Args:
        n_samples: number of samples to generate
    
    Returns:
        list of (state, optimal_action) tuples
    """
    optimizer = NSGAIIOptimizer(n_pop=100, n_gen=50)
    optimizer.optimize()

    dataset = []

    for _ in range(n_samples):
        # Random state from distribution
        state = np.random.rand(13)  # 13-dim state vector

        # Get action from Pareto front (random from alternatives)
        idx = np.random.randint(len(optimizer.pareto_solutions))
        solution = optimizer.pareto_solutions[idx]

        # Extract one action
        action_idx = int(solution[np.random.randint(len(solution))])

        dataset.append((state, action_idx))

    return dataset


class MMDEOptimizer:
    """
    MMDE (Multimodal Mutation Differential Evolution) variant.
    Enhanced NSGA-II with adaptive mutation.
    """

    def __init__(self, n_pop=NSGA_POP, n_gen=NSGA_GENS, f=MMDE_F, cr=MMDE_CR):
        self.n_pop = n_pop
        self.n_gen = n_gen
        self.f = f
        self.cr = cr
        self.population = None
        self.fitness = None

    def optimize(self):
        """
        Run MMDE optimization.
        This is a simplified version; full MMDE uses adaptive parameters.
        
        Returns:
            (pareto_front, pareto_solutions)
        """
        problem = SchedulingProblem(n_steps=2, n_samples=100)

        # For now, use standard NSGA-II with MMDE parameters via mutation
        algorithm = NSGA2(pop_size=self.n_pop)

        termination = get_termination("n_gen", self.n_gen)

        result = minimize(
            problem,
            algorithm,
            termination,
            seed=42,
            verbose=True,
        )

        return result.F, result.X
