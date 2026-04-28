"""
Professional dataset generation for PCNME experiments.
Generates realistic mobility patterns and task workloads.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path


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
