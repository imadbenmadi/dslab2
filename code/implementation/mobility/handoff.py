import numpy as np
from config import FOG_NODES, FOG_COVERAGE_RADIUS, FOG_MIPS

class TrajectoryPredictor:
    """Predicts vehicle trajectory and handoff opportunities."""

    def compute_distance(self, vehicle_pos: tuple, fog_pos: tuple) -> float:
        """Euclidean distance in metres."""
        return np.sqrt((vehicle_pos[0]-fog_pos[0])**2 + (vehicle_pos[1]-fog_pos[1])**2)

    def compute_t_exit(self, vehicle_pos: tuple, vehicle_speed_ms: float,
                       vehicle_heading_deg: float, fog_id: str) -> float:
        """Estimate time until vehicle exits fog coverage area."""
        fog_pos = FOG_NODES[fog_id]['pos']
        dist = self.compute_distance(vehicle_pos, fog_pos)

        if dist >= FOG_COVERAGE_RADIUS:
            return 0.0  # already outside zone

        # Direction vector from vehicle to fog centre
        dx = fog_pos[0] - vehicle_pos[0]
        dy = fog_pos[1] - vehicle_pos[1]
        to_fog_angle = np.degrees(np.arctan2(dy, dx))

        # Vehicle velocity components
        heading_rad = np.radians(vehicle_heading_deg)
        vx = vehicle_speed_ms * np.cos(heading_rad)
        vy = vehicle_speed_ms * np.sin(heading_rad)

        # Closing speed toward fog boundary (positive = moving away from centre)
        # Project velocity onto outward radial direction
        if dist < 1e-6:
            return float('inf')
        radial_x, radial_y = -dx/dist, -dy/dist   # outward from fog centre
        v_closing = vx * radial_x + vy * radial_y  # positive = moving toward boundary

        if v_closing <= 0:
            return float('inf')  # moving toward fog centre, won't exit soon

        return (FOG_COVERAGE_RADIUS - dist) / v_closing

    def compute_t_exec(self, step_MI: int, fog_id: str, fog_load: float) -> float:
        """Execution time accounting for fog node load."""
        return (step_MI / FOG_MIPS) / max(1 - fog_load, 0.05)

    def predict_next_fog(self, vehicle_pos: tuple, vehicle_speed_ms: float,
                         vehicle_heading_deg: float, t_exit: float,
                         current_fog: str) -> str:
        """Predict next fog node based on vehicle trajectory."""
        heading_rad = np.radians(vehicle_heading_deg)
        future_x = vehicle_pos[0] + vehicle_speed_ms * np.cos(heading_rad) * t_exit
        future_y = vehicle_pos[1] + vehicle_speed_ms * np.sin(heading_rad) * t_exit

        best_id = None
        best_dist = 1e18
        for fog_id, fog_data in FOG_NODES.items():
            if fog_id == current_fog:
                continue
            dist = self.compute_distance((future_x, future_y), fog_data['pos'])
            if dist <= FOG_COVERAGE_RADIUS and dist < best_dist:
                best_dist = dist
                best_id = fog_id

        return best_id if best_id else 'CLOUD'  # no fog zone found at predicted position

    def select_mode(self, t_exit: float, t_exec: float) -> str:
        """Select handoff mode based on execution time and exit time."""
        if t_exec < t_exit:
            return 'DIRECT'
        return 'PROACTIVE'


class HTBBuffer:
    """
    Handoff Task Buffer — high-priority queue for in-flight tasks
    whose vehicle has disconnected unexpectedly.
    """
    def __init__(self):
        self.buffer = {}   # task_id -> {'step': step, 'vehicle_id': vid}
        self.completed = {}  # vehicle_id -> [results]

    def push(self, task_id: str, step, vehicle_id: str):
        """Move task from NTB to HTB on unexpected disconnection."""
        self.buffer[task_id] = {'step': step, 'vehicle_id': vehicle_id}

    def complete(self, task_id: str, result: dict):
        """Mark task as complete, hold result for vehicle."""
        if task_id in self.buffer:
            vid = self.buffer.pop(task_id)['vehicle_id']
            if vid not in self.completed:
                self.completed[vid] = []
            self.completed[vid].append(result)

    def deliver_on_reconnect(self, vehicle_id: str) -> list:
        """Called when vehicle reconnects to any fog node."""
        results = self.completed.pop(vehicle_id, [])
        return results

    @property
    def queue_size(self):
        return len(self.buffer)
