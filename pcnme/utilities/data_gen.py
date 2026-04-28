"""
Professional dataset generation for PCNME experiments.
Generates realistic mobility patterns and task workloads.
"""

import numpy as np
import csv
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from pcnme.optimization import NSGAIIOptimizer, SchedulingProblem
from pcnme import STATE_DIM, ACTION_DIM
from pcnme.progress import progress
from tqdm import tqdm


class MobilityGenerator:
    """Generate realistic vehicle mobility patterns."""
    
    def __init__(self, scenario: str = "urban", seed: int = 42):
        """
        Initialize mobility generator.
        
        Args:
            scenario: 'urban', 'highway', or 'mixed'
            seed: random seed
        """
        self.scenario = scenario
        self.rng = np.random.default_rng(seed)
        
        # Scenario parameters (speed, direction changes, coverage area)
        self.params = {
            'urban': {
                'speed_range': (10, 50),        # km/h
                'turn_probability': 0.3,         # change direction every ~3.3 steps
                'coverage_area': (10000, 10000), # 10km x 10km
            },
            'highway': {
                'speed_range': (80, 120),
                'turn_probability': 0.05,
                'coverage_area': (50000, 5000),
            },
            'mixed': {
                'speed_range': (30, 80),
                'turn_probability': 0.15,
                'coverage_area': (20000, 15000),
            }
        }
    
    def generate_trace(self, vehicle_id: str, duration_s: int = 1800, dt_s: float = 1.0) -> Dict:
        """
        Generate a realistic vehicle trace.
        
        Args:
            vehicle_id: unique vehicle identifier
            duration_s: trace duration in seconds
            dt_s: timestep in seconds
            
        Returns:
            dict with xs, ys, speeds, headings, timestamps
        """
        params = self.params[self.scenario]
        speed_min, speed_max = params['speed_range']
        coverage_x, coverage_y = params['coverage_area']
        
        n_steps = int(duration_s / dt_s)
        
        # Initialize trajectory
        x = self.rng.uniform(0, coverage_x)
        y = self.rng.uniform(0, coverage_y)
        heading = self.rng.uniform(0, 360)
        speed_kmh = self.rng.uniform(speed_min, speed_max)
        speed_ms = speed_kmh / 3.6
        
        xs, ys, speeds, headings, timestamps = [], [], [], [], []
        
        for step in range(n_steps):
            xs.append(x)
            ys.append(y)
            speeds.append(speed_ms)
            headings.append(heading)
            timestamps.append(step * dt_s)
            
            # Update heading (random walk in angle space)
            if self.rng.random() < params['turn_probability']:
                dtheta = self.rng.uniform(-45, 45)
                heading = (heading + dtheta) % 360
            
            # Update speed (realistic acceleration/deceleration)
            dspeed = self.rng.uniform(-2, 2)  # m/s change
            speed_ms = np.clip(speed_ms + dspeed, speed_min / 3.6, speed_max / 3.6)
            
            # Update position
            x_new = x + speed_ms * dt_s * np.cos(np.radians(heading))
            y_new = y + speed_ms * dt_s * np.sin(np.radians(heading))
            
            # Bounce at boundaries
            if x_new < 0 or x_new > coverage_x:
                heading = (180 - heading) % 360
                x_new = np.clip(x_new, 0, coverage_x)
            if y_new < 0 or y_new > coverage_y:
                heading = (360 - heading) % 360
                y_new = np.clip(y_new, 0, coverage_y)
            
            x, y = x_new, y_new
        
        return {
            'vehicle_id': vehicle_id,
            'scenario': self.scenario,
            'xs': np.array(xs),
            'ys': np.array(ys),
            'speeds': np.array(speeds),
            'headings': np.array(headings),
            'timestamps': np.array(timestamps),
        }


class TaskWorkloadGenerator:
    """Generate realistic task workloads."""
    
    def __init__(self, scenario: str = "normal", seed: int = 42):
        """
        Initialize task workload generator.
        
        Args:
            scenario: 'light', 'normal', 'heavy'
            seed: random seed
        """
        self.scenario = scenario
        self.rng = np.random.default_rng(seed)
        
        # Workload parameters
        self.params = {
            'light': {
                'arrival_rate': 0.5,      # tasks per minute per vehicle
                'data_size_kb_range': (100, 500),
                'deadline_ms_range': (200, 400),
            },
            'normal': {
                'arrival_rate': 1.0,
                'data_size_kb_range': (200, 1000),
                'deadline_ms_range': (150, 300),
            },
            'heavy': {
                'arrival_rate': 2.0,
                'data_size_kb_range': (500, 2000),
                'deadline_ms_range': (100, 200),
            }
        }
    
    def generate_workload(self, duration_s: int = 1800) -> List[Dict]:
        """
        Generate task arrivals during duration.
        
        Returns:
            list of dicts with task_id, arrival_time_s, data_kb, deadline_ms
        """
        params = self.params[self.scenario]
        arrival_rate = params['arrival_rate']
        data_min, data_max = params['data_size_kb_range']
        deadline_min, deadline_max = params['deadline_ms_range']
        
        # Poisson process for task arrivals
        lambda_rate = arrival_rate / 60.0  # per second
        n_tasks = self.rng.poisson(lambda_rate * duration_s)
        
        arrival_times = np.sort(self.rng.uniform(0, duration_s, n_tasks))
        
        tasks = []
        for i, arrival_time in enumerate(arrival_times):
            tasks.append({
                'task_id': i,
                'arrival_time_s': arrival_time,
                'data_kb': self.rng.uniform(data_min, data_max),
                'deadline_ms': self.rng.uniform(deadline_min, deadline_max),
            })
        
        return tasks


class RealisticDatasetGenerator:
    """Generate complete realistic dataset for PCNME."""
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
    
    def generate_scenario(self, scenario: str, n_vehicles: int = 50, duration_s: int = 1800):
        """
        Generate complete scenario: mobility + workload.
        
        Args:
            scenario: 'morning_rush', 'off_peak', 'evening_rush'
            n_vehicles: number of vehicles
            duration_s: simulation duration
            
        Returns:
            dict with traces and workloads
        """
        # Map scenario to mobility/workload patterns
        scenario_map = {
            'morning_rush': ('urban', 'heavy'),
            'off_peak': ('mixed', 'light'),
            'evening_rush': ('urban', 'heavy'),
        }
        
        mobility_type, workload_type = scenario_map.get(scenario, ('mixed', 'normal'))
        
        # Generate mobility
        mobility_gen = MobilityGenerator(mobility_type, seed=self.seed)
        traces = []
        for i in range(n_vehicles):
            trace = mobility_gen.generate_trace(f"v_{i:04d}", duration_s)
            traces.append(trace)
        
        # Generate workload
        workload_gen = TaskWorkloadGenerator(workload_type, seed=self.seed)
        workload = workload_gen.generate_workload(duration_s)
        
        return {
            'scenario': scenario,
            'traces': traces,
            'workload': workload,
            'n_vehicles': n_vehicles,
            'duration_s': duration_s,
        }
    
    def generate_dataset(self, output_dir: Optional[Path] = None) -> Dict:
        """
        Generate complete 3-scenario dataset.
        
        Returns:
            dict with datasets for each scenario
        """
        dataset = {}
        for scenario in ['morning_rush', 'off_peak', 'evening_rush']:
            dataset[scenario] = self.generate_scenario(scenario, n_vehicles=50, duration_s=1800)
        
        return dataset


def generate_bc_dataset(n_batches: int = 20, batch_size: int = 100, seed: int = 42, logger=None):
    """
    Generate behavioral cloning dataset from REAL NSGA-II Pareto-optimal solutions.
    Default size: 2,000 highly optimized state-action pairs.
    """
    if logger is None:
        logger = logging.getLogger('PCNME.Pretrain')
    
    logger.info(f"Running NSGA-II optimization for expert trajectories...")
    
    optimizer = NSGAIIOptimizer()
    optimizer.optimize()
    
    pareto_solutions = np.asarray(optimizer.pareto_pop)

    if len(pareto_solutions) == 0:
        logger.warning("No Pareto solutions found, using random dataset")
        pareto_solutions = np.random.randint(0, 5, (10, 3)).astype(float)
    
    logger.info(f"[OK] Extracted {len(pareto_solutions)} Pareto-optimal solutions")
    
    # Calculate experiments dir dynamically from utilities folder
    exp_dir = Path(__file__).parent.parent / 'experiments'
    
    nsga_path = exp_dir / 'results' / 'pretraining' / 'tof_nsga_solutions.csv'
    nsga_path.parent.mkdir(parents=True, exist_ok=True)
    with open(nsga_path, 'w', newline='') as f:
        writer = csv.writer(f)
        num_actions = pareto_solutions.shape[1] if pareto_solutions.ndim == 2 else 1
        writer.writerow([f"action_step_{i+1}" for i in range(num_actions)])
        for sol in pareto_solutions:
            writer.writerow(sol if pareto_solutions.ndim == 2 else [sol])
    logger.info(f"[OK] NSGA-II solutions saved to {nsga_path}")

    logger.info(f"[OK] Generating BC dataset: {n_batches} batches x {batch_size} samples")
    
    dataset = []
    rng = np.random.default_rng(seed)

    batch_iter = progress(range(n_batches), desc="BC dataset", unit="batch", total=n_batches)
    
    for batch_idx in batch_iter:
        rhos = rng.uniform(0.20, 0.75, (batch_size, 4))
        qs = rng.uniform(0.0, 1.0, (batch_size, 4))
        mi_choices = np.array([200, 500, 800, 1000, 1200, 1500, 1800])
        l_j = rng.choice(mi_choices, batch_size)
        ec_norm = np.clip((l_j / 2000.0) / 1.0, 0, 1).reshape(-1, 1)
        s_i = rng.normal(16.67, 4.17, batch_size)
        s_norm = np.clip(s_i / 33.3, 0, 1).reshape(-1, 1)
        t_exit_norm = rng.uniform(0.0, 1.0, (batch_size, 1))
        states = np.hstack([rhos, qs, ec_norm, s_norm, t_exit_norm])

        actions = []
        # Cool progress bar for the real math optimization!
        for i in tqdm(range(batch_size), desc=f"Optimizing Batch {batch_idx+1}/{n_batches}", leave=False):
            prob = SchedulingProblem(state_vector=states[i])
            real_optimizer = NSGAIIOptimizer(problem=prob, pop_size=20, n_gen=10)
            real_optimizer.optimize()
            _, best_chromosome = real_optimizer.get_knee_point()
            actions.append(int(best_chromosome[0]))

        for i in range(batch_size):
            dataset.append((states[i], int(actions[i])))
            
    dataset_path = exp_dir / 'dataset' / 'gen_BC_dataset.csv'
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(dataset_path, 'w', newline='') as f:
        writer = csv.writer(f)
        header = ['fog_A_load', 'fog_B_load', 'fog_C_load', 'fog_D_load', 'fog_A_queue', 'fog_B_queue', 'fog_C_queue', 'fog_D_queue', 'exec_cost_norm', 'speed_norm', 't_exit_norm', 'action']
        writer.writerow(header)
        for state, action in dataset:
            writer.writerow(list(state) + [action])
    logger.info(f"[OK] Total dataset size: {len(dataset)} samples")
    return dataset
