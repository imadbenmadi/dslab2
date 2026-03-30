import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from config import DAG_STEPS, TOTAL_DEADLINE_MS

# Real YOLOv5 latency data (milliseconds)
YOLO_LATENCY_BENCHMARKS = {
    'yolov5s_device': 50,      # On-device preprocessing
    'yolov5s_preprocessing': 15,  # Image resize, normalization
    'yolov5s_inference': 80,    # Actual inference
    'yolov5s_postprocessing': 10, # NMS, output formatting
}

@dataclass
class DAGStep:
    """Represents a single DAG step in a computation pipeline."""
    step_id: int
    MI: int
    in_KB: float
    out_KB: float
    name: str
    deadline_ms: float
    result: Optional[float] = None
    assigned_to: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    # Real latency data
    latency_benchmarks: Dict = field(default_factory=dict)

@dataclass
class DAGTask:
    """Task representing a computation pipeline with multiple stages."""
    task_id: str
    vehicle_id: str
    created_at: float
    steps: Dict[int, DAGStep]
    spatial_tag: Dict
    total_deadline_ms: float = TOTAL_DEADLINE_MS

    @property
    def is_complete(self):
        return all(s.end_time is not None for s in self.steps.values()
                   if s.assigned_to != 'device')

    @property
    def total_latency_ms(self):
        if not self.is_complete:
            return None
        times = [s.end_time for s in self.steps.values() if s.end_time]
        start = min(s.start_time for s in self.steps.values() if s.start_time)
        return (max(times) - start) * 1000

    @property
    def deadline_met(self):
        if self.total_latency_ms is None:
            return False
        return self.total_latency_ms <= self.total_deadline_ms

def generate_dag_task(task_id: str, vehicle_id: str, sim_time: float,
                      spatial_tag: Dict) -> DAGTask:
    """
    Generate a realistic YOLOv5 object detection DAG task.
    
    Real structure based on YOLO inference pipeline:
    - Total end-to-end: ~200ms target
    - Can be distributed across device/fog/cloud
    """
    steps = {}
    for sid, spec in DAG_STEPS.items():
        # Use real YOLOv5 latency for inference steps
        latency_bench = {}
        if 'inference' in spec['name'].lower():
            latency_bench = YOLO_LATENCY_BENCHMARKS.copy()
        
        steps[sid] = DAGStep(
            step_id=sid,
            MI=spec['MI'],
            in_KB=spec['in_KB'],
            out_KB=spec['out_KB'],
            name=spec['name'],
            deadline_ms=spec.get('deadline_ms', TOTAL_DEADLINE_MS),
            assigned_to=spec.get('runs_on', None),
            latency_benchmarks=latency_bench,
        )
    return DAGTask(task_id=task_id, vehicle_id=vehicle_id,
                   created_at=sim_time, steps=steps, spatial_tag=spatial_tag)
