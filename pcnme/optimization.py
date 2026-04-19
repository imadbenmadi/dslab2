"""
Multi-objective optimization: NSGA-II and MMDE.
"""

import numpy as np
from typing import Tuple, List

from .constants import (
    NSGA_POP, NSGA_GENS, MMDE_F, MMDE_CR, N_OFFLINE_BATCHES,
    DAG, FOG_NODES, STATE_DIM, ACTION_DIM
)


class SchedulingProblem:
    """Multi-objective optimization problem for task scheduling."""

    def __init__(self):
        self.n_pebble_steps = 3  # Steps 2, 3, 5
        self.n_objectives = 2  # latency, energy

    def evaluate(self, assignment: np.ndarray) -> np.ndarray:
        """
        Evaluate scheduling assignment.
        assignment: array of [peb2_dest, peb3_dest, peb5_dest]
                   where each value is 0-3 (fog A-D) or 4 (cloud)
        Returns: [total_latency_ms, total_energy_j]
        """
        from .formulas import step_latency, step_energy, classify_step

        # Simulate task execution
        total_latency = 0.0
        total_energy = 0.0

        # Step 1 (device)
        step1_info = DAG[1]
        total_latency += step1_info["in_KB"] * 8 / 100 + 10  # rough estimate
        total_energy += 0.01

        # Steps 2, 3, 4, 5
        steps = [2, 3, 4, 5]
        pebble_map = {2: assignment[0], 3: assignment[1], 5: assignment[2]}

        for step_id in steps:
            step_info = DAG[step_id]
            step_MI = step_info["MI"]
            data_KB = step_info["in_KB"]

            if classify_step(step_MI) == "boulder":
                dest = "cloud"
            else:
                dest_idx = pebble_map[step_id]
                dest = ["A", "B", "C", "D", "cloud"][int(dest_idx)]

            lat = step_latency(step_MI, data_KB, dest, fog_load=0.3)
            eng = step_energy(step_MI, data_KB, dest)
            total_latency += lat
            total_energy += eng

        return np.array([total_latency, total_energy])


class NSGAIIOptimizer:
    """NSGA-II multi-objective optimizer."""

    def __init__(self, problem: SchedulingProblem, pop_size: int = NSGA_POP,
                 n_gen: int = NSGA_GENS):
        self.problem = problem
        self.pop_size = pop_size
        self.n_gen = n_gen

    def optimize(self) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        """
        Run NSGA-II optimization.
        Returns: (pareto_front_objectives, pareto_solutions)
        """
        # Simplified NSGA-II: random initialization + selection
        pop = np.random.randint(0, 5, (self.pop_size, 3)).astype(float)
        fitness = np.array([self.problem.evaluate(ind) for ind in pop])

        for gen in range(self.n_gen):
            # Simple mutation
            new_pop = pop.copy()
            for i in range(self.pop_size):
                if np.random.random() < 0.3:
                    idx = np.random.randint(3)
                    new_pop[i, idx] = np.random.randint(0, 5)

            new_fitness = np.array([self.problem.evaluate(ind) for ind in new_pop])

            # Simple selection: keep best by first objective
            combined = np.vstack([pop, new_pop])
            combined_fitness = np.vstack([fitness, new_fitness])
            indices = np.argsort(combined_fitness[:, 0])[:self.pop_size]
            pop = combined[indices]
            fitness = combined_fitness[indices]

        # Extract Pareto front
        pareto_indices = self._get_pareto_front(fitness)
        pareto_fitness = fitness[pareto_indices]
        pareto_pop = pop[pareto_indices]

        return list(pareto_fitness), list(pareto_pop)

    def _get_pareto_front(self, fitness: np.ndarray) -> np.ndarray:
        """Get indices of non-dominated solutions."""
        is_dominated = np.zeros(len(fitness), dtype=bool)
        for i in range(len(fitness)):
            for j in range(len(fitness)):
                if i != j:
                    if (fitness[j] <= fitness[i]).all() and (fitness[j] < fitness[i]).any():
                        is_dominated[i] = True
                        break
        return np.where(~is_dominated)[0]

    def get_knee_point(self, objectives: List[np.ndarray]) -> np.ndarray:
        """Find knee point (best compromise) solution."""
        objectives = np.array(objectives)
        if len(objectives) == 0:
            return np.array([1, 1, 1])

        # Normalized distance to utopian point
        min_lat = objectives[:, 0].min()
        max_lat = objectives[:, 0].max()
        min_eng = objectives[:, 1].min()
        max_eng = objectives[:, 1].max()

        normalized = np.zeros_like(objectives)
        if max_lat > min_lat:
            normalized[:, 0] = (objectives[:, 0] - min_lat) / (max_lat - min_lat)
        else:
            normalized[:, 0] = 0.5
        if max_eng > min_eng:
            normalized[:, 1] = (objectives[:, 1] - min_eng) / (max_eng - min_eng)
        else:
            normalized[:, 1] = 0.5

        distance = np.sqrt((normalized**2).sum(axis=1))
        knee_idx = np.argmin(distance)
        return knee_idx


class MMDEOptimizer:
    """Multimodal Mutation Differential Evolution."""

    def __init__(self, problem: SchedulingProblem, pop_size: int = NSGA_POP,
                 n_gen: int = NSGA_GENS, F: float = MMDE_F, CR: float = MMDE_CR):
        self.problem = problem
        self.pop_size = pop_size
        self.n_gen = n_gen
        self.F = F
        self.CR = CR

    def optimize(self) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        """Run MMDE optimization."""
        pop = np.random.randint(0, 5, (self.pop_size, 3)).astype(float)
        fitness = np.array([self.problem.evaluate(ind) for ind in pop])

        for gen in range(self.n_gen):
            # Adaptive mutation
            for i in range(self.pop_size):
                r1, r2, r3 = np.random.choice(self.pop_size, 3, replace=False)
                mutant = np.clip(pop[r1] + self.F * (pop[r2] - pop[r3]), 0, 4)

                # Crossover
                trial = pop[i].copy()
                for j in range(3):
                    if np.random.random() < self.CR:
                        trial[j] = mutant[j]

                trial_fitness = self.problem.evaluate(trial)
                if trial_fitness[0] < fitness[i, 0]:  # better on first objective
                    pop[i] = trial
                    fitness[i] = trial_fitness

        pareto_indices = self._get_pareto_front(fitness)
        return list(fitness[pareto_indices]), list(pop[pareto_indices])

    def _get_pareto_front(self, fitness: np.ndarray) -> np.ndarray:
        """Get Pareto front indices."""
        is_dominated = np.zeros(len(fitness), dtype=bool)
        for i in range(len(fitness)):
            for j in range(len(fitness)):
                if i != j:
                    if (fitness[j] <= fitness[i]).all() and (fitness[j] < fitness[i]).any():
                        is_dominated[i] = True
                        break
        return np.where(~is_dominated)[0]


def generate_bc_dataset_from_nsga2(n_samples: int = N_OFFLINE_BATCHES) -> List[Tuple]:
    """
    Generate behavioral cloning dataset from NSGA-II Pareto front.
    Returns list of (state, action) tuples.
    """
    from .formulas import build_state

    problem = SchedulingProblem()
    optimizer = NSGAIIOptimizer(problem)
    pareto_objectives, pareto_solutions = optimizer.optimize()

    dataset = []
    for _ in range(n_samples):
        # Random state
        fog_loads = {
            "A": np.random.uniform(0.2, 0.7),
            "B": np.random.uniform(0.2, 0.7),
            "C": np.random.uniform(0.2, 0.7),
            "D": np.random.uniform(0.2, 0.7),
        }
        fog_queues = {
            "A": np.random.randint(0, 20),
            "B": np.random.randint(0, 20),
            "C": np.random.randint(0, 20),
            "D": np.random.randint(0, 20),
        }
        step_MI = np.random.choice([20, 200, 2000, 8000, 50])
        vehicle_speed = np.random.uniform(5, 20)
        t_exit = np.random.uniform(1, 10)
        deadline_remaining = np.random.uniform(50, 200)

        state = build_state(fog_loads, fog_queues, step_MI, 0.5,
                           vehicle_speed, t_exit, deadline_remaining)

        # Pick random Pareto solution as target action
        if pareto_solutions:
            solution = pareto_solutions[np.random.randint(len(pareto_solutions))]
            # Map to action (0-4)
            action = int(solution[0] % 5)
            dataset.append((state, action))

    return dataset
