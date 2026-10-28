import numpy as np
from config import FOG_NODES, FOG_COVERAGE_RADIUS

class CityGrid:
    """Manages urban grid and fog node coverage areas."""
    def __init__(self, width: int = 1000, height: int = 1000):
        self.width = width
        self.height = height
        self.fog_nodes = FOG_NODES
        self.coverage_radius = FOG_COVERAGE_RADIUS
    
    def get_fog_in_range(self, position: tuple) -> list:
        """Get all fog nodes within range of given position"""
        in_range = []
        for fog_id, fog_data in self.fog_nodes.items():
            dist = np.sqrt((position[0] - fog_data['pos'][0])**2 + 
                          (position[1] - fog_data['pos'][1])**2)
            if dist <= self.coverage_radius:
                in_range.append(fog_id)
        return in_range
