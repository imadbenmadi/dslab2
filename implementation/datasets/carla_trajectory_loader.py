"""
CARLA Trajectory Data Loader

Loads real vehicle trajectories from carla_trajectories.csv
and provides them to vehicle movement simulation.

The CSV contains Istanbul city data with:
- vehicle_id, timestamp_s, position_x, position_y, speed_kmh, heading_deg
"""

import csv
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class CarlaTrajectoryLoader:
    """Load and provide access to real vehicle trajectories from CARLA."""
    
    def __init__(self, csv_path: str = "results/carla_trajectories.csv"):
        self.csv_path = Path(csv_path)
        self.trajectories: Dict[str, List[Dict]] = defaultdict(list)
        self.timestamp_range = (float('inf'), float('-inf'))
        self.vehicle_ids = set()
        self._load_trajectories()
    
    def _load_trajectories(self):
        """Load all trajectories from CSV."""
        if not self.csv_path.exists():
            print(f"[CarlaTrajectoryLoader] Warning: {self.csv_path} not found")
            return
        
        print(f"[CarlaTrajectoryLoader] Loading trajectories from {self.csv_path}...")
        
        try:
            with open(self.csv_path, 'r') as f:
                reader = csv.DictReader(f)
                row_count = 0
                
                for row in reader:
                    vehicle_id = row.get('vehicle_id', f"vehicle_{row_count}")
                    timestamp_s = float(row.get('timestamp_s', 0.0))
                    position_x = float(row.get('position_x', 0.0))
                    position_y = float(row.get('position_y', 0.0))
                    speed_kmh = float(row.get('speed_kmh', 0.0))
                    heading_deg = float(row.get('heading_deg', 0.0))
                    
                    # Convert speed from km/h to m/s
                    speed_ms = speed_kmh * (1000 / 3600)
                    
                    # Track timestamp range
                    self.timestamp_range = (
                        min(self.timestamp_range[0], timestamp_s),
                        max(self.timestamp_range[1], timestamp_s)
                    )
                    
                    # Store trajectory point
                    self.trajectories[vehicle_id].append({
                        'timestamp_s': timestamp_s,
                        'position_x': position_x,
                        'position_y': position_y,
                        'speed_kmh': speed_kmh,
                        'speed_ms': speed_ms,
                        'heading_deg': heading_deg,
                    })
                    
                    self.vehicle_ids.add(vehicle_id)
                    row_count += 1
            
            print(f"[CarlaTrajectoryLoader] [OK]  Loaded {len(self.vehicle_ids)} vehicles, "
                  f"{row_count} trajectory points")
            print(f"[CarlaTrajectoryLoader] Time range: {self.timestamp_range[0]:.1f}s - {self.timestamp_range[1]:.1f}s")
            
            # Sort each vehicle's trajectory by timestamp
            for vehicle_id in self.trajectories:
                self.trajectories[vehicle_id].sort(key=lambda x: x['timestamp_s'])
        
        except Exception as e:
            print(f"[CarlaTrajectoryLoader] ✗ Error loading trajectories: {e}")
    
    def get_position_at_time(self, vehicle_id: str, sim_time_s: float, 
                            cycle: bool = True) -> Optional[Tuple[float, float, float, float]]:
        """
        Get vehicle position at given simulation time.
        
        Returns: (x, y, speed_ms, heading_deg) or None if vehicle not found
        
        Args:
            vehicle_id: Vehicle identifier (e.g., "vehicle_000")
            sim_time_s: Simulation time in seconds
            cycle: If True, cycle trajectory when reaching end; if False, stop at end
        """
        
        if vehicle_id not in self.trajectories or not self.trajectories[vehicle_id]:
            return None
        
        traj = self.trajectories[vehicle_id]
        
        if cycle:
            # Cycle trajectory by wrapping time
            traj_duration = traj[-1]['timestamp_s'] - traj[0]['timestamp_s']
            if traj_duration > 0:
                cycled_time = traj[0]['timestamp_s'] + (sim_time_s % traj_duration)
            else:
                cycled_time = sim_time_s
        else:
            cycled_time = min(sim_time_s, traj[-1]['timestamp_s'])
        
        # Find closest trajectory point
        best_point = None
        best_diff = float('inf')
        
        for point in traj:
            diff = abs(point['timestamp_s'] - cycled_time)
            if diff < best_diff:
                best_diff = diff
                best_point = point
        
        if best_point:
            return (
                best_point['position_x'],
                best_point['position_y'],
                best_point['speed_ms'],
                best_point['heading_deg']
            )
        
        return None
    
    def get_trajectory_segment(self, vehicle_id: str, start_time_s: float, 
                              end_time_s: float) -> List[Dict]:
        """Get trajectory points within time segment."""
        
        if vehicle_id not in self.trajectories:
            return []
        
        traj = self.trajectories[vehicle_id]
        segment = [p for p in traj if start_time_s <= p['timestamp_s'] <= end_time_s]
        
        return segment
    
    def get_random_vehicle(self) -> Optional[str]:
        """Get a random vehicle ID."""
        if self.vehicle_ids:
            return np.random.choice(list(self.vehicle_ids))
        return None
    
    def get_initial_position(self, vehicle_id: str) -> Optional[Tuple[float, float]]:
        """Get vehicle's initial position."""
        if vehicle_id not in self.trajectories or not self.trajectories[vehicle_id]:
            return None
        
        first_point = self.trajectories[vehicle_id][0]
        return (first_point['position_x'], first_point['position_y'])
    
    @property
    def vehicle_count(self) -> int:
        """Number of unique vehicles in dataset."""
        return len(self.vehicle_ids)
    
    @property
    def duration_s(self) -> float:
        """Total trajectory duration in seconds."""
        if self.timestamp_range[1] == float('-inf'):
            return 0.0
        return self.timestamp_range[1] - self.timestamp_range[0]


# Global trajectory loader instance
_trajectory_loader: Optional[CarlaTrajectoryLoader] = None

def get_trajectory_loader(csv_path: str = "results/carla_trajectories.csv") -> CarlaTrajectoryLoader:
    """Get or create the global trajectory loader."""
    global _trajectory_loader
    
    if _trajectory_loader is None:
        _trajectory_loader = CarlaTrajectoryLoader(csv_path)
    
    return _trajectory_loader

def reset_trajectory_loader():
    """Reset the trajectory loader (for testing)."""
    global _trajectory_loader
    _trajectory_loader = None
