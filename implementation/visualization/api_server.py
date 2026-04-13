"""
REST API Server for React Dashboard
Provides endpoints for system status, history, and configuration
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import threading
import os
import numpy as np
from typing import Dict, List, Any
from collections import deque
from storage.data_store import get_data_store
from results.baseline_results import get_baseline_tracker
from .websocket_server import get_ws_server, SystemMetrics


app = Flask(__name__, static_folder='../frontend/build', static_url_path='')
CORS(app)


# In-memory metrics history (last 100 records)
metrics_history: deque = deque(maxlen=100)


class SimulationState:
    """Track simulation state"""
    def __init__(self):
        self.is_running = False
        self.current_time = 0.0
        self.total_time = 900.0  # 15 minutes
        self.system_type = 'proposed'  # baseline1, baseline2, baseline3, proposed
        self.progress = 0.0
        
    def to_dict(self):
        return {
            'isRunning': self.is_running,
            'currentTime': self.current_time,
            'totalTime': self.total_time,
            'systemType': self.system_type,
            'progress': self.progress
        }


sim_state = SimulationState()
_storage = get_data_store()

# Runtime callbacks injected by app.py to control live simulation worker.
_start_callback = None
_stop_callback = None
_reset_callback = None
_logic_callback = None
_tasks_callback = None
_logs_callback = None


def set_runtime_callbacks(
    start_callback=None,
    stop_callback=None,
    reset_callback=None,
    logic_callback=None,
    tasks_callback=None,
    logs_callback=None,
):
    """Inject live runtime callbacks from the orchestrator entrypoint."""
    global _start_callback, _stop_callback, _reset_callback, _logic_callback, _tasks_callback, _logs_callback
    _start_callback = start_callback
    _stop_callback = stop_callback
    _reset_callback = reset_callback
    _logic_callback = logic_callback
    _tasks_callback = tasks_callback
    _logs_callback = logs_callback


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'storage': _storage.status(),
    })


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current simulation status"""
    return jsonify(sim_state.to_dict())


@app.route('/api/metrics/current', methods=['GET'])
def get_current_metrics():
    """Get latest metrics"""
    latest = _storage.read_latest_metric()
    if latest:
        return jsonify(latest)

    if metrics_history:
        return jsonify(metrics_history[-1])
    return jsonify({
        'error': 'No metrics available yet'
    }), 404


@app.route('/api/metrics/history', methods=['GET'])
def get_metrics_history():
    """Get metrics history"""
    limit = request.args.get('limit', default=50, type=int)
    persisted = _storage.read_metrics_history(limit=limit)
    if persisted:
        return jsonify(persisted)

    history_list = list(metrics_history)[-limit:]
    return jsonify(history_list)


@app.route('/api/evaluation/summary', methods=['GET'])
def get_evaluation_summary():
    """Return richer statistical summary over the currently collected metrics history."""
    data = _storage.read_metrics_history(limit=500)
    if not data:
        data = list(metrics_history)

    if not data:
        return jsonify({'error': 'No metrics available yet'}), 404

    lat = np.asarray([float(m.get('avgLatency', 0.0)) for m in data], dtype=float)
    suc = np.asarray([float(m.get('successRate', 0.0)) for m in data], dtype=float)
    thr = np.asarray([float(m.get('throughput', 0.0)) for m in data], dtype=float)

    def _ci(arr):
        if arr.size == 0:
            return (0.0, 0.0, 0.0)
        if arr.size == 1:
            v = float(arr[0])
            return (v, v, v)
        rng = np.random.default_rng(42)
        means = []
        for _ in range(600):
            s = rng.choice(arr, size=arr.size, replace=True)
            means.append(float(np.mean(s)))
        return (
            float(np.mean(arr)),
            float(np.percentile(means, 2.5)),
            float(np.percentile(means, 97.5)),
        )

    def _slope(arr):
        if arr.size < 2:
            return 0.0
        x = np.arange(arr.size, dtype=float)
        m, _ = np.polyfit(x, arr, 1)
        return float(m)

    lat_m, lat_lo, lat_hi = _ci(lat)
    suc_m, suc_lo, suc_hi = _ci(suc)
    thr_m, thr_lo, thr_hi = _ci(thr)

    return jsonify({
        'windowSize': int(len(data)),
        'latency': {'mean': lat_m, 'ci95Low': lat_lo, 'ci95High': lat_hi, 'trendPerTick': _slope(lat)},
        'successRate': {'mean': suc_m, 'ci95Low': suc_lo, 'ci95High': suc_hi, 'trendPerTick': _slope(suc)},
        'throughput': {'mean': thr_m, 'ci95Low': thr_lo, 'ci95High': thr_hi, 'trendPerTick': _slope(thr)},
    }), 200


@app.route('/api/simulation/start', methods=['POST'])
def start_simulation():
    """Start simulation"""
    data = request.get_json() or {}
    sim_state.system_type = data.get('systemType', 'proposed')
    sim_state.is_running = True
    sim_state.current_time = 0.0
    sim_state.progress = 0.0
    
    response = {
        'message': 'Simulation started',
        'systemType': sim_state.system_type
    }

    if _start_callback:
        callback_out = _start_callback(sim_state.system_type)
        if isinstance(callback_out, dict):
            response.update(callback_out)

    return jsonify(response)


@app.route('/api/simulation/stop', methods=['POST'])
def stop_simulation():
    """Stop simulation"""
    sim_state.is_running = False
    response = {'message': 'Simulation stopped'}
    if _stop_callback:
        callback_out = _stop_callback()
        if isinstance(callback_out, dict):
            response.update(callback_out)
    return jsonify(response)


@app.route('/api/simulation/reset', methods=['POST'])
def reset_simulation():
    """Reset simulation"""
    sim_state.is_running = False
    sim_state.current_time = 0.0
    sim_state.progress = 0.0
    metrics_history.clear()
    _storage.clear_runtime()
    response = {'message': 'Simulation reset'}
    if _reset_callback:
        callback_out = _reset_callback()
        if isinstance(callback_out, dict):
            response.update(callback_out)
    return jsonify(response)


@app.route('/api/logic/snapshot', methods=['GET'])
def get_logic_snapshot():
    """Get live logic/pipeline snapshot from orchestrator."""
    if _logic_callback:
        return jsonify(_logic_callback())
    return jsonify({'logic': {}, 'agent': {}, 'bootstrap': {}})


@app.route('/api/tasks/recent', methods=['GET'])
def get_tasks_recent():
    """Get recent processed task events."""
    limit = request.args.get('limit', default=100, type=int)
    persisted = _storage.read_recent_tasks(limit=limit)
    if persisted:
        return jsonify({'items': persisted})

    if _tasks_callback:
        return jsonify({'items': _tasks_callback()})
    return jsonify({'items': []})


@app.route('/api/logs/recent', methods=['GET'])
def get_logs_recent():
    """Get recent structured runtime logs."""
    limit = request.args.get('limit', default=100, type=int)
    persisted = _storage.read_recent_logs(limit=limit)
    if persisted:
        return jsonify({'items': persisted})

    if _logs_callback:
        return jsonify({'items': _logs_callback()})
    return jsonify({'items': []})


@app.route('/api/analytics/window', methods=['GET'])
def get_analytics_window():
    """Get aggregated analytics for a historical window (default 1h)."""
    window = (request.args.get('window', default='1h', type=str) or '1h').strip().lower()
    if window == '24h':
        hours = 24
    elif window == '1h':
        hours = 1
    else:
        hours = request.args.get('hours', default=1, type=int)

    result = _storage.read_analytics_window(hours=hours)
    return jsonify(result), 200


@app.route('/api/analytics/vehicle/<vehicle_id>', methods=['GET'])
def get_analytics_by_vehicle(vehicle_id: str):
    """Get vehicle-specific analytics for a historical window (default 24h)."""
    window = (request.args.get('window', default='24h', type=str) or '24h').strip().lower()
    if window == '1h':
        hours = 1
    elif window == '24h':
        hours = 24
    else:
        hours = request.args.get('hours', default=24, type=int)

    limit = request.args.get('limit', default=200, type=int)
    summary = _storage.read_vehicle_analytics_window(vehicle_id=vehicle_id, hours=hours)
    items = _storage.read_task_window(hours=hours, limit=limit, vehicle_id=vehicle_id)
    return jsonify({'summary': summary, 'items': items}), 200


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get system configuration"""
    return jsonify({
        'numVehicles': 50,
        'numFogNodes': 4,
        'cloudLatency': 30,
        'taskDeadline': 380,
        'fogCompute': 2000,
        'cloudCompute': 8000,
        'simulationDuration': 900,
    })


@app.route('/api/baselines', methods=['GET'])
def get_baselines():
    """Get baseline comparison data - returns real results from runs or defaults."""
    tracker = get_baseline_tracker()
    comparison = tracker.get_system_comparison()
    
    # Ensure all baselines are present with defaults if needed
    defaults = {
        'baseline1': {
            'name': 'Pure NSGA-II',
            'successRate': 47.0,
            'avgLatency': 167.2,
            'totalEnergy': 250.5,
        },
        'baseline2': {
            'name': 'TOF + NSGA-II',
            'successRate': 68.4,
            'avgLatency': 205.2,
            'totalEnergy': 265.3,
        },
        'baseline3': {
            'name': 'TOF + MMDE-NSGA-II',
            'successRate': 80.4,
            'avgLatency': 163.0,
            'totalEnergy': 242.1,
        },
    }
    
    result = {}
    for key in ['baseline1', 'baseline2', 'baseline3']:
        if key in comparison and comparison[key]:
            result[key] = comparison[key]
        else:
            result[key] = defaults[key]
    
    return jsonify(result)


@app.route('/api/system-info', methods=['GET'])
def get_system_info():
    """Get system information"""
    return jsonify({
        'name': 'Smart City Vehicular Task Offloading System',
        'version': '1.0',
        'location': 'Istanbul',
        'vehicles': 50,
        'fogNodes': 4,
        'cloudServers': 1,
        'datasets': {
            'trajectories': 'CARLA (50 vehicles)',
            'taskBenchmarks': 'YOLOv5 real latencies',
            'networkTraces': 'CRAWDAD 4G',
        }
    })


@app.route('/api/export', methods=['GET'])
def export_data():
    """Export current metrics history as CSV"""
    data = _storage.read_metrics_history(limit=5000)
    if not data:
        data = list(metrics_history)

    if not data:
        return jsonify({'error': 'No data to export'}), 404
    
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    first_metric = data[0]
    writer.writerow(first_metric.keys())
    
    # Write data
    for metric in data:
        writer.writerow(metric.values())
    
    return output.getvalue(), 200, {
        'Content-Disposition': 'attachment; filename=metrics.csv',
        'Content-Type': 'text/csv'
    }


@app.route('/api/map/state', methods=['GET'])
def get_map_state():
    """Get map visualization state: vehicles, connections, handoffs, coverage zones"""
    ws_server = get_ws_server()
    
    if not ws_server:
        return jsonify({
            'vehicles': [],
            'fogNodes': [],
            'cloud': [],
            'connections': [],
            'handoffs': [],
            'coverageZones': [],
            'timestamp': datetime.now().isoformat()
        })
    
    latest_state = ws_server.latest_state or {}
    
    # Build map structure
    map_state = {
        'vehicles': latest_state.get('vehicles', []),
        'fogNodes': latest_state.get('fogNodes', []),
        'cloud': latest_state.get('cloud', {}),
        'connections': latest_state.get('connections', []),
        'handoffs': latest_state.get('handoffs', []),
        'coverageZones': latest_state.get('coverageZones', []),
        'timestamp': datetime.now().isoformat()
    }
    
    return jsonify(map_state)


@app.route('/api/map/connections', methods=['GET'])
def get_connections():
    """Get all active connections on the network (task offloads, fog-to-fog relays, handoffs)"""
    ws_server = get_ws_server()
    
    if not ws_server:
        return jsonify({'connections': [], 'count': 0})
    
    latest_state = ws_server.latest_state or {}
    connections = latest_state.get('connections', [])
    
    # Group by type
    by_type = {}
    for conn in connections:
        conn_type = conn.get('type', 'unknown')
        if conn_type not in by_type:
            by_type[conn_type] = []
        by_type[conn_type].append(conn)
    
    return jsonify({
        'connections': connections,
        'count': len(connections),
        'byType': by_type,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/map/handoffs', methods=['GET'])
def get_handoffs():
    """Get all recent handoff events"""
    ws_server = get_ws_server()
    
    if not ws_server:
        return jsonify({'handoffs': [], 'count': 0})
    
    latest_state = ws_server.latest_state or {}
    handoffs = latest_state.get('handoffs', [])
    
    return jsonify({
        'handoffs': handoffs,
        'count': len(handoffs),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/map/trajectory/<vehicle_id>', methods=['GET'])
def get_vehicle_trajectory(vehicle_id):
    """Get trajectory prediction for a specific vehicle"""
    ws_server = get_ws_server()
    
    if not ws_server:
        return jsonify({
            'vehicleId': vehicle_id,
            'trajectory': [],
            't_exit': None,
            'nextFog': None
        })
    
    latest_state = ws_server.latest_state or {}
    vehicles = latest_state.get('vehicles', [])
    
    vehicle = None
    for v in vehicles:
        if v.get('id') == vehicle_id:
            vehicle = v
            break
    
    if not vehicle:
        return jsonify({
            'vehicleId': vehicle_id,
            'trajectory': [],
            't_exit': None,
            'nextFog': None
        }), 404
    
    return jsonify({
        'vehicleId': vehicle_id,
        'trajectory': vehicle.get('trajectoryWaypoints', []),
        'position': {'x': vehicle.get('x'), 'y': vehicle.get('y')},
        'heading': vehicle.get('heading_deg', 0),
        'speed': vehicle.get('speed_kmh', 0),
        't_exit': vehicle.get('t_exit', None),
        'nextFog': vehicle.get('nextFog', None),
        'currentFog': vehicle.get('currentFog', None),
        'timestamp': datetime.now().isoformat()
    })


# React app routing
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    """Serve React app"""
    static_folder = app.static_folder
    if static_folder and path and os.path.exists(os.path.join(static_folder, path)):
        return send_from_directory(static_folder, path)

    # If a production React build exists, serve it.
    if static_folder and os.path.exists(os.path.join(static_folder, 'index.html')):
        return send_from_directory(static_folder, 'index.html')

    # Fallback for development mode where React runs on :3000.
    return jsonify({
        'message': 'API server is running',
        'dashboard': 'http://localhost:3000',
        'health': '/api/health'
    }), 200


def add_metrics(metrics_dict: Dict[str, Any]):
    """Add metrics to history (called from simulation)"""
    metrics_history.append(metrics_dict)
    _storage.write_metric(metrics_dict)


def add_task_event(task_event: Dict[str, Any]):
    """Persist a task event for API retrieval."""
    _storage.write_task_event(task_event)


def add_runtime_log(log_event: Dict[str, Any]):
    """Persist runtime structured logs for API retrieval."""
    _storage.write_runtime_log(log_event)


def update_simulation_time(current_time: float):
    """Update simulation time"""
    sim_state.current_time = current_time
    sim_state.progress = (current_time / sim_state.total_time) * 100


def run_api_server(host='127.0.0.1', port=5000, debug=False):
    """Run Flask API server"""
    app.run(host=host, port=port, debug=debug, threaded=True)


def run_api_server_thread(host='127.0.0.1', port=5000):
    """Run Flask API server in background thread"""
    thread = threading.Thread(
        target=run_api_server,
        args=(host, port),
        daemon=True
    )
    thread.start()
    return thread


if __name__ == '__main__':
    run_api_server(debug=True)
