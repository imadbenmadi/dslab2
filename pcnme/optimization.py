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

    def __init__(self, state_vector: np.ndarray = None):
        self.state_vector = state_vector
        self.n_pebble_steps = 1 if state_vector is not None else 3  # Steps 2, 3, 5
        self.n_objectives = 2  # latency, energy

    def evaluate(self, assignment: np.ndarray) -> np.ndarray:
        """
        Evaluate scheduling assignment.
        Returns: [total_latency_ms, total_energy_j]
        """
        from .formulas import step_latency, step_energy, classify_step

        if self.state_vector is not None:
            dest_idx = int(assignment[0])
            ec = self.state_vector[8]      # exec_cost_norm
            t_exit = self.state_vector[10] # t_exit_norm
            
            if dest_idx == 4:
                lat = 80.0 + (ec * 150.0) 
                eng = 0.5 + (ec * 0.8)
            else:
                fog_load = self.state_vector[dest_idx]
                fog_queue = self.state_vector[dest_idx + 4]
                lat = 10.0 + (ec * 50.0) / max(0.01, 1.0 - fog_load) + (fog_queue * 15.0)
                eng = 0.1 + (ec * 0.3)
                if t_exit < 0.2:
                    lat += 300.0  
                    eng += 1.5
            return np.array([lat, eng])

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
    """NSGA-II multi-objective optimizer with MMDE."""

    def __init__(self, problem: SchedulingProblem = None, pop_size: int = NSGA_POP,
                 n_gen: int = NSGA_GENS):
        if problem is None:
            problem = SchedulingProblem()
        self.problem = problem
        self.pop_size = pop_size
        self.n_gen = n_gen
        self.pareto_pop = []
        self.pareto_fitness = []

    def optimize(self) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        """
        Run NSGA-II optimization with MMDE mutations.
        Returns: (pareto_front_objectives, pareto_solutions)
        """
        # Initialize population
        pop = np.random.randint(0, 5, (self.pop_size, self.problem.n_pebble_steps)).astype(float)
        fitness = np.array([self.problem.evaluate(ind) for ind in pop])

        for gen in range(self.n_gen):
            # MMDE mutation for diversity
            new_pop = self._mmde_mutation(pop)
            new_fitness = np.array([self.problem.evaluate(ind) for ind in new_pop])

            # Combine and select best via non-dominated sorting
            combined_pop = np.vstack([pop, new_pop])
            combined_fitness = np.vstack([fitness, new_fitness])

            # Fast non-dominated sorting
            fronts = self._fast_nondominated_sort(combined_fitness)
            
            # Select new population
            pop = []
            fitness_list = []
            for front in fronts:
                if len(pop) + len(front) <= self.pop_size:
                    pop.extend(combined_pop[front])
                    fitness_list.extend(combined_fitness[front])
                else:
                    # Crowding distance for last front
                    remaining = self.pop_size - len(pop)
                    dist = self._crowding_distance(combined_fitness[front])
                    selected_idx = np.argsort(-dist)[:remaining]
                    pop.extend(combined_pop[front[selected_idx]])
                    fitness_list.extend(combined_fitness[front[selected_idx]])
                    break

            pop = np.array(pop[:self.pop_size])
            fitness = np.array(fitness_list[:self.pop_size])

        # Extract Pareto front from final population
        pareto_indices = self._get_pareto_front(fitness)
        self.pareto_fitness = fitness[pareto_indices]
        self.pareto_pop = pop[pareto_indices]

        return list(self.pareto_fitness), list(self.pareto_pop)

    def _mmde_mutation(self, pop: np.ndarray) -> np.ndarray:
        """Apply MMDE (Multimodal Mutation Differential Evolution) mutations."""
        n_pop = len(pop)
        mutant_pop = []

        for i in range(n_pop):
            # Select three random distinct individuals
            idx = np.random.choice(n_pop, 3, replace=False)
            r1, r2, r3 = idx[0], idx[1], idx[2]

            # MMDE mutation: v = pop[r1] + F * (pop[r2] - pop[r3])
            mutant = pop[r1] + MMDE_F * (pop[r2] - pop[r3])
            mutant = np.clip(mutant, 0, 4)  # Clamp to valid range

            # Binomial crossover with CR
            trial = pop[i].copy()
            for j in range(self.problem.n_pebble_steps):
                if np.random.random() < MMDE_CR:
                    trial[j] = mutant[j]

            mutant_pop.append(trial.astype(float))

        return np.array(mutant_pop)

    def _fast_nondominated_sort(self, fitness: np.ndarray):
        """Fast non-dominated sorting (Deb et al., 2002)."""
        n = len(fitness)
        domination_count = np.zeros(n)
        dominated_solutions = [[] for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                if (fitness[i] <= fitness[j]).all() and (fitness[i] < fitness[j]).any():
                    dominated_solutions[i].append(j)
                    domination_count[j] += 1
                elif (fitness[j] <= fitness[i]).all() and (fitness[j] < fitness[i]).any():
                    dominated_solutions[j].append(i)
                    domination_count[i] += 1

        fronts = []
        front = np.where(domination_count == 0)[0]
        while len(front) > 0:
            fronts.append(front)
            next_front = []
            for i in front:
                for j in dominated_solutions[i]:
                    domination_count[j] -= 1
                    if domination_count[j] == 0:
                        next_front.append(j)
            front = np.array(next_front)

        return fronts

    def _crowding_distance(self, fitness: np.ndarray) -> np.ndarray:
        """Calculate crowding distance for fitness values."""
        n = len(fitness)
        distance = np.zeros(n)

        for m in range(fitness.shape[1]):
            sorted_idx = np.argsort(fitness[:, m])
            distance[sorted_idx[0]] = distance[sorted_idx[-1]] = float('inf')

            f_min = fitness[sorted_idx[0], m]
            f_max = fitness[sorted_idx[-1], m]

            if f_max - f_min > 0:
                for i in range(1, n - 1):
                    distance[sorted_idx[i]] += (fitness[sorted_idx[i + 1], m] - 
                                                fitness[sorted_idx[i - 1], m]) / (f_max - f_min)

        return distance

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

    def get_knee_point(self) -> Tuple[int, np.ndarray]:
        """Find knee point (best compromise) solution from Pareto front."""
        if len(self.pareto_fitness) == 0:
            return 0, np.array([1, 1, 1])

        objectives = self.pareto_fitness
        
        # Normalize objectives
        min_lat = objectives[:, 0].min()
        max_lat = objectives[:, 0].max()
        min_eng = objectives[:, 1].min()
        max_eng = objectives[:, 1].max()

        normalized = np.zeros_like(objectives, dtype=float)
        if max_lat > min_lat:
            normalized[:, 0] = (objectives[:, 0] - min_lat) / (max_lat - min_lat)
        else:
            normalized[:, 0] = 0.5
        if max_eng > min_eng:
            normalized[:, 1] = (objectives[:, 1] - min_eng) / (max_eng - min_eng)
        else:
            normalized[:, 1] = 0.5

        # Distance to Utopian point (0, 0)
        distance = np.sqrt((normalized**2).sum(axis=1))
        knee_idx = np.argmin(distance)
        
        return int(knee_idx), self.pareto_pop[knee_idx]


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
        pop = np.random.randint(0, 5, (self.pop_size, self.problem.n_pebble_steps)).astype(float)
        fitness = np.array([self.problem.evaluate(ind) for ind in pop])

        for gen in range(self.n_gen):
            # Adaptive mutation
            for i in range(self.pop_size):
                r1, r2, r3 = np.random.choice(self.pop_size, 3, replace=False)
                mutant = np.clip(pop[r1] + self.F * (pop[r2] - pop[r3]), 0, 4)

                # Crossover
                trial = pop[i].copy()
                for j in range(self.problem.n_pebble_steps):
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
