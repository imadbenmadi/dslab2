"""
PCNME Data Generation and Mobility Traces
Handles real datasets (Roma CRAWDAD, SF Cabspotting) and synthetic traces.
"""

import numpy as np
from pathlib import Path
from .constants import SCENARIO_SPEEDS, SIM_DURATION_S, FOG_RADIUS


def synthetic_traces(scenario: str, n_vehicles: int = 50, seed: int = 42,
                     duration_s: float = 600.0) -> list:
    """
    Generate synthetic vehicle mobility traces using Random Waypoint model.
    
    Speed distribution calibrated from Roma taxi statistics.
    Traces are generated on a 1000m x 1000m grid.
    
    Args:
        scenario: 'morning_rush', 'off_peak', or 'evening_rush'
        n_vehicles: number of vehicles
        seed: random seed for reproducibility
        duration_s: simulation duration (seconds)
    
    Returns:
        list of trace dictionaries, each containing:
        {
            'vehicle_id': str,
            'xs': list of x positions,
            'ys': list of y positions,
            'speeds': list of speeds (m/s),
            'headings': list of headings (degrees),
            'timestamps': list of times (seconds),
        }
    """
    assert scenario in SCENARIO_SPEEDS, f"Unknown scenario: {scenario}"
    
    params = SCENARIO_SPEEDS[scenario]
    rng = np.random.default_rng(seed)
    traces = []
    dt = 1.0  # 1-second ticks
    times = np.arange(0, duration_s, dt)
    n_steps = len(times)
    
    for vid in range(n_vehicles):
        # Initialize random position and waypoint
        x, y = rng.uniform(0, 1000, 2)
        wx, wy = rng.uniform(0, 1000, 2)
        speed = max(1.0, rng.normal(params["mean"], params["std"]))
        
        xs, ys, speeds, headings = [], [], [], []
        
        for _ in range(n_steps):
            # Distance to waypoint
            dx, dy = wx - x, wy - y
            dist = np.sqrt(dx**2 + dy**2)
            
            # Reached waypoint: pick new one
            if dist < speed * dt:
                wx, wy = rng.uniform(0, 1000, 2)
                speed = max(1.0, rng.normal(params["mean"], params["std"]))
                dx, dy = wx - x, wy - y
                dist = np.sqrt(dx**2 + dy**2)
            
            # Compute heading
            heading = (np.degrees(np.arctan2(dy, dx)) + 360) % 360
            
            # Update position
            x_new = float(np.clip(
                x + speed * dt * np.cos(np.radians(heading)), 0, 1000
            ))
            y_new = float(np.clip(
                y + speed * dt * np.sin(np.radians(heading)), 0, 1000
            ))
            
            xs.append(x_new)
            ys.append(y_new)
            speeds.append(float(speed))
            headings.append(float(heading))
            
            x, y = x_new, y_new
        
        traces.append({
            'vehicle_id': f'v{vid:03d}',
            'xs': xs,
            'ys': ys,
            'speeds': speeds,
            'headings': headings,
            'timestamps': list(times),
        })
    
    return traces


def load_roma_taxi_dataset(data_dir: Path, limit_taxis: int = None) -> dict:
    """
    Load Roma CRAWDAD taxi dataset if available.
    
    Dataset structure:
    - Downloaded from https://crawdad.org/roma/taxi/20140717/
    - Each taxi has CSV file: taxi_id, lat, lon, occupancy, timestamp
    
    Args:
        data_dir: directory containing extracted taxi data
        limit_taxis: max number of taxis to load (for testing)
    
    Returns:
        dict mapping taxi_id -> traces (same format as synthetic_traces)
    
    Returns empty dict if dataset not found.
    """
    roma_dir = data_dir / 'roma_taxi'
    if not roma_dir.exists():
        print(f"Roma dataset not found at {roma_dir}")
        return {}
    
    traces = {}
    csv_files = list(roma_dir.glob('*.csv'))
    
    if limit_taxis:
        csv_files = csv_files[:limit_taxis]
    
    for csv_file in csv_files:
        try:
            taxi_id = csv_file.stem
            data = np.loadtxt(csv_file, delimiter=',', skiprows=0)
            
            # data shape: (n_points, 5)
            # columns: taxi_id, lat, lon, occupancy, timestamp
            lats = data[:, 1]
            lons = data[:, 2]
            times = data[:, 4]
            
            # Normalize coordinates to 1000x1000m grid
            # (approximate, using simple scaling)
            xs = ((lons - lons.min()) / (lons.max() - lons.min())) * 1000
            ys = ((lats - lats.min()) / (lats.max() - lats.min())) * 1000
            
            # Compute speeds from consecutive positions
            dxs = np.diff(xs)
            dys = np.diff(ys)
            dts = np.diff(times)
            dts[dts == 0] = 1  # avoid division by zero
            speeds = np.sqrt(dxs**2 + dys**2) / dts
            
            # Compute headings
            headings = (np.degrees(np.arctan2(dys, dxs)) + 360) % 360
            
            traces[taxi_id] = {
                'vehicle_id': taxi_id,
                'xs': xs.tolist(),
                'ys': ys.tolist(),
                'speeds': np.clip(speeds, 1.0, 40.0).tolist(),  # clip outliers
                'headings': headings.tolist(),
                'timestamps': times.tolist(),
            }
        except Exception as e:
            print(f"Error loading {csv_file}: {e}")
            continue
    
    return traces


def load_sf_cabspotting(data_file: Path) -> dict:
    """
    Load San Francisco Cabspotting dataset if available.
    
    Dataset structure:
    - Downloaded from https://www.cs.ucsf.edu/~varocha/data/cabspotting/
    - Format: lat lon occupancy timestamp (space-separated)
    
    Args:
        data_file: path to cabspottingdata file
    
    Returns:
        dict mapping cab_id -> traces
    
    Returns empty dict if dataset not found.
    """
    if not data_file.exists():
        print(f"SF Cabspotting dataset not found at {data_file}")
        return {}
    
    traces = {}
    
    try:
        with open(data_file, 'r') as f:
            current_cab_id = None
            lats, lons, times = [], [], []
            
            for line_no, line in enumerate(f):
                parts = line.strip().split()
                if len(parts) < 4:
                    continue
                
                lat, lon, occupancy, timestamp = map(float, parts[:4])
                cab_id = int(parts[4]) if len(parts) > 4 else 0
                
                # New cab ID: save previous trace
                if cab_id != current_cab_id and current_cab_id is not None:
                    if len(lats) > 1:
                        xs = ((np.array(lons) - np.array(lons).min()) /
                              (np.array(lons).max() - np.array(lons).min())) * 1000
                        ys = ((np.array(lats) - np.array(lats).min()) /
                              (np.array(lats).max() - np.array(lats).min())) * 1000
                        
                        dxs = np.diff(xs)
                        dys = np.diff(ys)
                        dts = np.diff(times)
                        dts[dts == 0] = 1
                        speeds = np.sqrt(dxs**2 + dys**2) / dts
                        headings = (np.degrees(np.arctan2(dys, dxs)) + 360) % 360
                        
                        traces[str(current_cab_id)] = {
                            'vehicle_id': f'sf_{current_cab_id}',
                            'xs': xs.tolist(),
                            'ys': ys.tolist(),
                            'speeds': np.clip(speeds, 1.0, 40.0).tolist(),
                            'headings': headings.tolist(),
                            'timestamps': times.copy(),
                        }
                
                current_cab_id = cab_id
                lats.append(lat)
                lons.append(lon)
                times.append(timestamp)
    
    except Exception as e:
        print(f"Error loading SF Cabspotting: {e}")
    
    return traces


class DataManager:
    """Manages loading and caching of mobility traces."""

    def __init__(self, data_dir: Path = Path('experiments/data')):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.traces_cache = {}

    def get_traces(self, scenario: str, n_vehicles: int = 50,
                   seed: int = 42, force_synthetic: bool = False) -> list:
        """
        Get mobility traces for a scenario.
        Tries real datasets first, falls back to synthetic.
        
        Args:
            scenario: 'morning_rush', 'off_peak', or 'evening_rush'
            n_vehicles: number of vehicles to use
            seed: random seed
            force_synthetic: if True, skip real datasets
        
        Returns:
            list of trace dictionaries
        """
        cache_key = (scenario, n_vehicles, seed)
        if cache_key in self.traces_cache:
            return self.traces_cache[cache_key]
        
        traces = []
        
        # Try Roma dataset
        if not force_synthetic:
            roma_traces = load_roma_taxi_dataset(self.data_dir, limit_taxis=n_vehicles)
            if roma_traces:
                traces = list(roma_traces.values())[:n_vehicles]
                print(f"Loaded {len(traces)} Roma taxi traces")
        
        # Try SF Cabspotting dataset
        if not traces and not force_synthetic:
            sf_traces = load_sf_cabspotting(self.data_dir / 'cabspottingdata.txt')
            if sf_traces:
                traces = list(sf_traces.values())[:n_vehicles]
                print(f"Loaded {len(traces)} SF Cabspotting traces")
        
        # Fall back to synthetic
        if not traces:
            print(f"Generating synthetic traces for scenario: {scenario}")
            traces = synthetic_traces(scenario, n_vehicles, seed)
        
        self.traces_cache[cache_key] = traces
        return traces


def interpolate_traces_to_duration(traces: list, target_duration_s: float) -> list:
    """
    Resample traces to specific duration.
    
    Args:
        traces: list of trace dicts
        target_duration_s: target duration in seconds
    
    Returns:
        resampled traces (or original if already sufficient length)
    """
    result = []
    
    for trace in traces:
        original_duration = trace['timestamps'][-1] - trace['timestamps'][0]
        
        if original_duration >= target_duration_s:
            # Truncate
            n_steps = int(target_duration_s) + 1
            result.append({
                'vehicle_id': trace['vehicle_id'],
                'xs': trace['xs'][:n_steps],
                'ys': trace['ys'][:n_steps],
                'speeds': trace['speeds'][:n_steps],
                'headings': trace['headings'][:n_steps],
                'timestamps': trace['timestamps'][:n_steps],
            })
        else:
            # Repeat or extend
            result.append(trace)
    
    return result
