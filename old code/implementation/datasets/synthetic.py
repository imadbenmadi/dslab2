"""
Synthetic dataset providers used by the simulation runtime.
"""

from typing import Dict, List, Tuple
from pathlib import Path
import csv

import numpy as np


class TrajectoryGenerator:
    """Generate deterministic urban trajectories for a vehicle fleet."""

    def __init__(self, num_vehicles: int, duration_s: float, sample_hz: int = 10, seed: int = 42):
        self.num_vehicles = max(1, int(num_vehicles))
        self.duration_s = max(1.0, float(duration_s))
        self.sample_hz = max(1, int(sample_hz))
        self.rng = np.random.default_rng(seed)

    def _generate_single(self, vid: int) -> Dict[str, List[Tuple[float, float]]]:
        n_samples = int(self.duration_s * self.sample_hz)

        center_x = float(self.rng.uniform(250.0, 750.0))
        center_y = float(self.rng.uniform(250.0, 750.0))
        radius = float(self.rng.uniform(60.0, 230.0))
        phase = float(self.rng.uniform(0.0, 2.0 * np.pi))
        angular_speed = float(self.rng.uniform(0.0015, 0.0045))

        positions: List[Tuple[float, float]] = []
        speeds: List[float] = []

        prev_x = center_x + radius * np.cos(phase)
        prev_y = center_y + radius * np.sin(phase)

        for i in range(n_samples):
            angle = phase + i * angular_speed + vid * 0.07
            x = center_x + radius * np.cos(angle) + self.rng.normal(0.0, 3.0)
            y = center_y + radius * np.sin(angle) + self.rng.normal(0.0, 3.0)

            x = float(np.clip(x, 10.0, 990.0))
            y = float(np.clip(y, 10.0, 990.0))
            positions.append((x, y))

            dx = x - prev_x
            dy = y - prev_y
            speed_ms = np.sqrt(dx * dx + dy * dy) * self.sample_hz
            speed_kmh = float(np.clip(speed_ms * 3.6, 20.0, 110.0))
            speeds.append(speed_kmh)

            prev_x, prev_y = x, y

        return {"positions": positions, "speeds": speeds}

    def generate_fleet(self) -> List[Dict[str, List[Tuple[float, float]]]]:
        return [self._generate_single(i) for i in range(self.num_vehicles)]


class NetworkBandwidthTrace:
    """Simple time-series bandwidth profile."""

    def __init__(self, profile: str = "urban_4g", horizon_s: int = 600, sample_hz: int = 1, seed: int = 42):
        self.profile = profile
        self.horizon_s = max(60, int(horizon_s))
        self.sample_hz = max(1, int(sample_hz))
        self.rng = np.random.default_rng(seed + 1)
        self.source = "synthetic"
        self.bandwidth_mbps = self._build_trace()

    def _load_from_csv(self) -> np.ndarray:
        csv_path = Path("results") / "network_bandwidth.csv"
        if not csv_path.exists():
            return np.array([], dtype=np.float32)

        values = []
        try:
            with csv_path.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    values.append(float(row.get("bandwidth_mbps", 0.0)))
        except Exception:
            return np.array([], dtype=np.float32)

        arr = np.asarray(values, dtype=np.float32)
        arr = np.clip(arr, 5.0, 200.0)
        return arr

    def _build_trace(self) -> np.ndarray:
        # Prefer real trace replay from dataset when available.
        csv_trace = self._load_from_csv()
        if csv_trace.size > 0:
            self.source = "results/network_bandwidth.csv"
            n = self.horizon_s * self.sample_hz
            if csv_trace.size >= n:
                return csv_trace[:n]
            reps = int(np.ceil(n / csv_trace.size))
            return np.tile(csv_trace, reps)[:n].astype(np.float32)

        n = self.horizon_s * self.sample_hz
        t = np.linspace(0.0, 1.0, n)

        if self.profile == "urban_5g":
            base = 120.0
            amplitude = 30.0
            noise = 8.0
        else:
            base = 70.0
            amplitude = 22.0
            noise = 10.0

        trend = base + amplitude * np.sin(2.0 * np.pi * (3.0 * t + 0.15))
        random_component = self.rng.normal(0.0, noise, size=n)
        trace = np.clip(trend + random_component, 8.0, 180.0)
        return trace.astype(np.float32)
