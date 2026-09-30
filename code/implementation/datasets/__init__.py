"""
Dataset providers: synthetic generators and the CARLA trajectory loader.
"""

from datasets.synthetic import TrajectoryGenerator, NetworkBandwidthTrace
from datasets.carla_trajectory_loader import (
    CarlaTrajectoryLoader,
    get_trajectory_loader,
    reset_trajectory_loader,
)
