"""
Enhanced Real-Time Map Visualization with Coverage Zones and Task Flows
Shows fog coverage areas, vehicle positions, connections, and task offloading
"""

import numpy as np
from typing import Dict, List, Tuple, Any
from config import FOG_NODES, FOG_COVERAGE_RADIUS, N_VEHICLES


class MapVisualizationModel:
    """Generates map state with coverage zones and task flow visualization."""

    # Color scheme for connectivity types
    COLORS = {
        'coverage_zone': 'rgba(255, 100, 100, 0.15)',  # Light red fill
        'coverage_boundary': '#FF4444',                 # Red circle
        'vehicle': '#00AA00',                           # Green
        'fog_node': '#0066FF',                          # Blue
        'cloud': '#FF6600',                             # Orange
        'connection_local': '#00DD00',                  # Light green
        'connection_fog': '#4488FF',                    # Light blue
        'connection_cloud': '#FFAA44',                  # Light orange
        'connection_fog_to_fog': '#8844FF',            # Purple (new: fog-to-fog)
        'handoff_transition': '#FF00FF',               # Magenta (handoff)
        'task_offload': '#FFFF00',                     # Yellow (active offload)
    }

    def __init__(self, width: int = 1000, height: int = 1000):
        self.width = width
        self.height = height

    def generate_coverage_zones(self) -> List[Dict[str, Any]]:
        """Generate coverage zone elements for each fog node."""
        zones = []
        for fog_id, fog_data in FOG_NODES.items():
            x, y = fog_data['pos']
            zones.append({
                'type': 'coverage_zone',
                'fogId': fog_id,
                'x': float(x),
                'y': float(y),
                'radius': float(FOG_COVERAGE_RADIUS),
                'fill': self.COLORS['coverage_zone'],
                'stroke': self.COLORS['coverage_boundary'],
                'strokeWidth': 2,
                'label': f"Fog {fog_id}\n({fog_data.get('name', fog_id)})",
                'load': float(fog_data.get('load', 0.3)),
            })
        return zones

    def generate_fog_nodes(self) -> List[Dict[str, Any]]:
        """Generate fog node marker elements."""
        nodes = []
        for fog_id, fog_data in FOG_NODES.items():
            x, y = fog_data['pos']
            nodes.append({
                'type': 'fog_node',
                'fogId': fog_id,
                'x': float(x),
                'y': float(y),
                'size': 15,
                'fill': self.COLORS['fog_node'],
                'label': f"Fog-{fog_id}",
                'mips': 2000,
                'load': float(fog_data.get('load', 0.3)),
            })
        return nodes

    def generate_cloud_node(self) -> Dict[str, Any]:
        """Generate cloud data center marker at center top."""
        return {
            'type': 'cloud',
            'id': 'cloud',
            'x': float(self.width / 2),
            'y': float(50),  # Top of map
            'size': 20,
            'fill': self.COLORS['cloud'],
            'label': 'Cloud DC',
            'mips': 8000,
        }

    def add_vehicle(self, vehicle_state: Dict[str, Any], 
                   connection_type: str = None) -> Dict[str, Any]:
        """
        Enhance vehicle position with connection visualization.
        
        vehicle_state: {id, x, y, speed_kmh, heading_deg, ...}
        connection_type: 'local' | 'fog' | 'cloud' | 'fog_to_fog' | 'handoff'
        """
        vehicle = {
            'type': 'vehicle',
            'vehicleId': vehicle_state.get('id', ''),
            'x': float(vehicle_state.get('x', 0)),
            'y': float(vehicle_state.get('y', 0)),
            'size': 8,
            'fill': self.COLORS['vehicle'],
            'heading': float(vehicle_state.get('heading_deg', 0)),
            'speed': float(vehicle_state.get('speed_kmh', 0)),
            'label': vehicle_state.get('id', ''),
        }

        # Add connection indicator if task is being offloaded
        if connection_type:
            destination = vehicle_state.get('offload_to', None)
            connection_color = self.COLORS.get(f'connection_{connection_type}', '#CCCCCC')
            
            vehicle['connection'] = {
                'type': connection_type,
                'destination': destination,
                'color': connection_color,
                'lineWidth': 2 if connection_type == 'task_offload' else 1,
                'lineDash': [5, 5] if connection_type == 'handoff' else [],
            }

        return vehicle

    def add_connection_line(self, from_pos: Tuple[float, float], 
                           to_pos: Tuple[float, float],
                           connection_type: str = 'fog',
                           task_id: str = None) -> Dict[str, Any]:
        """
        Create visual connection line between entities.
        
        connection_type: 'device_to_fog' | 'fog_to_fog' | 'fog_to_cloud' | 'handoff' | 'task_offload'
        """
        color_key = {
            'device_to_fog': 'connection_fog',
            'fog_to_fog': 'connection_fog_to_fog',
            'fog_to_cloud': 'connection_cloud',
            'handoff': 'handoff_transition',
            'task_offload': 'task_offload',
        }.get(connection_type, 'connection_fog')

        return {
            'type': 'connection',
            'from': {'x': float(from_pos[0]), 'y': float(from_pos[1])},
            'to': {'x': float(to_pos[0]), 'y': float(to_pos[1])},
            'connectionType': connection_type,
            'color': self.COLORS[color_key],
            'lineWidth': 2 if connection_type == 'task_offload' else 1,
            'lineDash': [5, 5] if connection_type == 'handoff' else [],
            'arrowSize': 5 if connection_type == 'task_offload' else 3,
            'taskId': task_id,
        }

    def add_trajectory_path(self, vehicle_id: str, waypoints: List[Tuple[float, float]],
                          highlight_idx: int = None) -> Dict[str, Any]:
        """Draw vehicle trajectory path with optional highlight for predicted next hop."""
        return {
            'type': 'trajectory',
            'vehicleId': vehicle_id,
            'waypoints': [{'x': float(wp[0]), 'y': float(wp[1])} for wp in waypoints],
            'color': '#CCCCAA',
            'lineWidth': 1,
            'lineDash': [2, 2],
            'highlightIdx': highlight_idx,
            'highlightColor': '#FFFF00',
        }

    def add_handoff_event(self, vehicle_pos: Tuple[float, float],
                         from_fog: str, to_fog: str,
                         task_id: str = None) -> Dict[str, Any]:
        """Visualize a handoff event between fog nodes."""
        from_fog_pos = FOG_NODES[from_fog]['pos']
        to_fog_pos = FOG_NODES[to_fog]['pos']

        return {
            'type': 'handoff_event',
            'vehiclePos': {'x': float(vehicle_pos[0]), 'y': float(vehicle_pos[1])},
            'fromFog': from_fog,
            'toFog': to_fog,
            'fromPos': {'x': float(from_fog_pos[0]), 'y': float(from_fog_pos[1])},
            'toPos': {'x': float(to_fog_pos[0]), 'y': float(to_fog_pos[1])},
            'color': self.COLORS['handoff_transition'],
            'taskId': task_id,
            'lineWidth': 3,
        }

    def build_complete_map_state(self, vehicles: List[Dict], 
                                active_tasks: List[Dict] = None,
                                handoffs: List[Dict] = None) -> Dict[str, Any]:
        """
        Build complete map visualization state.
        
        vehicles: [{id, x, y, speed_kmh, heading_deg, offload_to, connection_type}, ...]
        active_tasks: [{task_id, vehicle_id, destination, ...}, ...]
        handoffs: [{vehicle_id, from_fog, to_fog, task_id}, ...]
        """
        map_state = {
            'timestamp': None,
            'width': self.width,
            'height': self.height,
            'layers': {
                'coverage_zones': self.generate_coverage_zones(),
                'fog_nodes': self.generate_fog_nodes(),
                'cloud': [self.generate_cloud_node()],
                'vehicles': [],
                'connections': [],
                'trajectories': [],
                'handoffs': [],
                'taskFlows': [],
            },
            'legend': self._build_legend(),
        }

        # Add vehicles with their connections
        for vehicle in vehicles:
            vehicle_elem = self.add_vehicle(
                vehicle,
                connection_type=vehicle.get('connection_type')
            )
            map_state['layers']['vehicles'].append(vehicle_elem)

            # Add trajectory if available
            if 'trajectory_waypoints' in vehicle:
                traj = self.add_trajectory_path(
                    vehicle['id'],
                    vehicle['trajectory_waypoints'],
                    highlight_idx=vehicle.get('next_waypoint_idx')
                )
                map_state['layers']['trajectories'].append(traj)

        # Add active task offload connections
        if active_tasks:
            for task in active_tasks:
                v_pos = (task.get('vehicle_x', 0), task.get('vehicle_y', 0))
                dest = task.get('destination', 'unknown')
                
                if dest in FOG_NODES:
                    dest_pos = FOG_NODES[dest]['pos']
                elif dest == 'cloud':
                    dest_pos = (self.width / 2, 50)
                else:
                    continue

                conn = self.add_connection_line(
                    v_pos, dest_pos,
                    connection_type='task_offload',
                    task_id=task.get('task_id')
                )
                map_state['layers']['taskFlows'].append(conn)

        # Add handoff events
        if handoffs:
            for ho in handoffs:
                ho_elem = self.add_handoff_event(
                    (ho.get('vehicle_x', 0), ho.get('vehicle_y', 0)),
                    ho.get('from_fog', 'A'),
                    ho.get('to_fog', 'B'),
                    task_id=ho.get('task_id')
                )
                map_state['layers']['handoffs'].append(ho_elem)

        return map_state

    @staticmethod
    def _build_legend() -> Dict[str, List[Dict[str, str]]]:
        """Build legend for map visualization."""
        return {
            'entities': [
                {'label': 'Fog Node', 'color': MapVisualizationModel.COLORS['fog_node']},
                {'label': 'Cloud DC', 'color': MapVisualizationModel.COLORS['cloud']},
                {'label': 'Vehicle', 'color': MapVisualizationModel.COLORS['vehicle']},
                {'label': 'Coverage Zone', 'color': MapVisualizationModel.COLORS['coverage_zone']},
            ],
            'connections': [
                {'label': 'Local Execution', 'color': MapVisualizationModel.COLORS['connection_local']},
                {'label': 'Fog Offload', 'color': MapVisualizationModel.COLORS['connection_fog']},
                {'label': 'Cloud Offload', 'color': MapVisualizationModel.COLORS['connection_cloud']},
                {'label': 'Fog-to-Fog (Relay)', 'color': MapVisualizationModel.COLORS['connection_fog_to_fog']},
                {'label': 'Handoff', 'color': MapVisualizationModel.COLORS['handoff_transition']},
                {'label': 'Active Task', 'color': MapVisualizationModel.COLORS['task_offload']},
            ],
        }


# Singleton instance
_viz_model = None


def get_map_viz_model(width: int = 1000, height: int = 1000) -> MapVisualizationModel:
    """Get singleton map visualization model."""
    global _viz_model
    if _viz_model is None:
        _viz_model = MapVisualizationModel(width, height)
    return _viz_model
