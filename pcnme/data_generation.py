"""
Data generation: mobility traces from datasets or synthetic sources.
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Optional

from .constants import SCENARIO_SPEEDS, SIM_DURATION_S, FOG_NODES


def synthetic_traces(scenario: str, n_vehicles: int = 50, seed: int = 42,
                     duration_s: float = SIM_DURATION_S):
    """
    Random Waypoint mobility on 1000x1000m grid.
    Speed drawn from scenario-specific Gaussian matching Roma taxi data.
    """
    params = SCENARIO_SPEEDS[scenario]
    rng = np.random.default_rng(seed)
    traces = []
    dt = 1.0  # 1-second ticks
    times = list(range(int(duration_s)))

    for vid in range(n_vehicles):
        x, y = rng.uniform(0, 1000, 2)
        wx, wy = rng.uniform(0, 1000, 2)
        speed = max(1.0, rng.normal(params["mean"], params["std"]))
        xs, ys, speeds, headings = [], [], [], []

        for _ in times:
            dx, dy = wx - x, wy - y
            dist = (dx**2 + dy**2)**0.5
            if dist < speed * dt:
                wx, wy = rng.uniform(0, 1000, 2)
                speed = max(1.0, rng.normal(params["mean"], params["std"]))
                dx, dy = wx - x, wy - y
            heading = (np.degrees(np.arctan2(dy, dx)) + 360) % 360
            x = float(np.clip(x + speed * dt * np.cos(np.radians(heading)), 0, 1000))
            y = float(np.clip(y + speed * dt * np.sin(np.radians(heading)), 0, 1000))
            xs.append(x)
            ys.append(y)
            speeds.append(speed)
            headings.append(heading)

        traces.append({
            "vehicle_id": f"v{vid:03d}",
            "xs": xs,
            "ys": ys,
            "speeds": speeds,
            "headings": headings,
            "timestamps": times,
        })
    return traces


def load_roma_taxi_dataset(data_dir: Path, n_vehicles: Optional[int] = None,
                           seed: int = 42) -> Optional[List[Dict]]:
    """
    Load Roma taxi dataset from CRAWDAD.
    Expects CSV files in data_dir with format: taxi_id, lat, lon, occupancy, timestamp
    """
    data_path = data_dir / "roma_taxi"
    if not data_path.exists():
        return None

    traces = []
    taxi_files = list(data_path.glob("*.csv"))[:n_vehicles] if n_vehicles else list(data_path.glob("*.csv"))

    for taxi_file in taxi_files:
        try:
            with open(taxi_file, "r") as f:
                lines = f.readlines()[1:]  # skip header

            lat_lon = np.array([[float(line.split(",")[1]), float(line.split(",")[2])]
                               for line in lines])
            # Convert lat/lon to grid coordinates (simplified)
            xs = (lat_lon[:, 0] - lat_lon[:, 0].min()) / (lat_lon[:, 0].max() - lat_lon[:, 0].min()) * 1000
            ys = (lat_lon[:, 1] - lat_lon[:, 1].min()) / (lat_lon[:, 1].max() - lat_lon[:, 1].min()) * 1000

            # Compute speeds and headings
            dxs = np.diff(xs)
            dys = np.diff(ys)
            speeds = np.sqrt(dxs**2 + dys**2)
            headings = np.degrees(np.arctan2(dys, dxs))
            headings = (headings + 360) % 360

            traces.append({
                "vehicle_id": taxi_file.stem.replace("taxi_", ""),
                "xs": xs.tolist(),
                "ys": ys.tolist(),
                "speeds": speeds.tolist() + [speeds[-1]],  # pad last
                "headings": headings.tolist() + [headings[-1]],
                "timestamps": list(range(len(xs))),
            })
        except Exception:
            continue

    return traces if traces else None


def load_sf_cabspotting(data_dir: Path, n_vehicles: Optional[int] = None,
                        seed: int = 42) -> Optional[List[Dict]]:
    """
    Load SF Cabspotting dataset.
    Expects data files with format: lat lon occupancy timestamp
    """
    data_path = data_dir / "sf_cabspotting"
    if not data_path.exists():
        return None

    traces = []
    data_files = list(data_path.glob("*.txt"))[:n_vehicles] if n_vehicles else list(data_path.glob("*.txt"))

    for data_file in data_files:
        try:
            with open(data_file, "r") as f:
                lines = f.readlines()

            lat_lon = np.array([[float(line.split()[0]), float(line.split()[1])]
                               for line in lines])
            # Convert lat/lon to grid
            xs = (lat_lon[:, 0] - lat_lon[:, 0].min()) / (lat_lon[:, 0].max() - lat_lon[:, 0].min()) * 1000
            ys = (lat_lon[:, 1] - lat_lon[:, 1].min()) / (lat_lon[:, 1].max() - lat_lon[:, 1].min()) * 1000

            dxs = np.diff(xs)
            dys = np.diff(ys)
            speeds = np.sqrt(dxs**2 + dys**2)
            headings = np.degrees(np.arctan2(dys, dxs))
            headings = (headings + 360) % 360

            traces.append({
                "vehicle_id": data_file.stem,
                "xs": xs.tolist(),
                "ys": ys.tolist(),
                "speeds": speeds.tolist() + [speeds[-1]],
                "headings": headings.tolist() + [headings[-1]],
                "timestamps": list(range(len(xs))),
            })
        except Exception:
            continue

    return traces if traces else None


class DataManager:
    """Manages dataset caching and lazy loading."""

    def __init__(self, data_dir: Path = Path("experiments/data")):
        self.data_dir = data_dir
        self.cache = {}

    def get_traces(self, scenario: str, n_vehicles: int = 50,
                   seed: int = 42) -> List[Dict]:
        """Get traces, preferring real datasets over synthetic."""
        cache_key = (scenario, n_vehicles, seed)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Try Roma taxi
        traces = load_roma_taxi_dataset(self.data_dir, n_vehicles, seed)
        if traces:
            self.cache[cache_key] = traces
            return traces

        # Try SF Cabspotting
        traces = load_sf_cabspotting(self.data_dir, n_vehicles, seed)
        if traces:
            self.cache[cache_key] = traces
            return traces

        # Fall back to synthetic
        traces = synthetic_traces(scenario, n_vehicles, seed)
        self.cache[cache_key] = traces
        return traces
