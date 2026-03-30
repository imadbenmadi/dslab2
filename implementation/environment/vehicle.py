"""
Professional Vehicle Module with CARLA-based Trajectories
Uses real urban mobility patterns from Istanbul network
"""
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from environment.task import generate_dag_task

@dataclass
class Vehicle:
    """Mobile vehicle with sensor-based task generation."""
    vehicle_id: str
    position: Tuple[float, float]
    speed_kmh: float
    heading_deg: float
    waypoints: List[Tuple[float, float]] = field(default_factory=list)
    waypoint_idx: int = 0
    task_queue: List = field(default_factory=list)
    last_task_time: float = 0.0
    
    def update_position(self, dt: float):
        """Update vehicle position based on current heading and speed"""
        speed_ms = self.speed_kmh / 3.6
        heading_rad = np.radians(self.heading_deg)
        dx = speed_ms * np.cos(heading_rad) * dt
        dy = speed_ms * np.sin(heading_rad) * dt
        
        # Wrap around grid boundaries
        new_x = (self.position[0] + dx) % 1000
        new_y = (self.position[1] + dy) % 1000
        self.position = (new_x, new_y)
    
    def generate_task(self, task_id: str, sim_time: float) -> Optional[object]:
        """
        Generate a new DAG task based on real YOLOv5 workload.
        Called at 10 fps (every 100ms for camera).
        """
        # Tasks generated every 100ms (10 fps camera)
        if sim_time - self.last_task_time < 0.1:
            return None
        
        self.last_task_time = sim_time
        
        spatial_tag = {
            'position': self.position,
            'speed_kmh': self.speed_kmh,
            'heading_deg': self.heading_deg,
        }
        
        task = generate_dag_task(task_id, self.vehicle_id, sim_time, spatial_tag)
        self.task_queue.append(task)
        return task
    
    def follow_trajectory(self, trajectory_waypoints: List[Tuple[float, float]],
                         trajectory_speeds: np.ndarray,
                         sim_time: float):
        """Follow CARLA-generated trajectory"""
        # Calculate how many waypoints we should have traversed
        elapsed = sim_time * 10  # 10 Hz sampling
        self.waypoint_idx = int(elapsed) % len(trajectory_waypoints)
        
        if self.waypoint_idx < len(trajectory_waypoints):
            self.position = trajectory_waypoints[self.waypoint_idx]
            self.speed_kmh = trajectory_speeds[self.waypoint_idx]
            
            # Calculate heading to next waypoint
            if self.waypoint_idx + 1 < len(trajectory_waypoints):
                next_wp = trajectory_waypoints[self.waypoint_idx + 1]
                dx = next_wp[0] - self.position[0]
                dy = next_wp[1] - self.position[1]
                self.heading_deg = np.degrees(np.arctan2(dy, dx))
