"""
Complete Cloud Server Implementation
Processes boulder-class tasks with realistic latencies and queue management
"""

import simpy
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Callable
from config import CLOUD_MIPS, WAN_LATENCY_MS


@dataclass
class CloudServer:
    """Central cloud server for task processing."""
    name: str = "Cloud"
    mips: int = CLOUD_MIPS         # 8000 MIPS
    env: Optional[simpy.Environment] = None
    
    # Queue management
    ntb_queue: List = field(default_factory=list)  # Normal Task Buffer
    load: float = 0.0
    
    # Network parameters
    wan_latency_ms: float = WAN_LATENCY_MS  # 30ms round-trip
    
    # Metrics
    processed_tasks: int = 0
    total_processing_time: float = 0.0
    task_completion_callback: Optional[Callable] = None
    
    def __post_init__(self):
        if self.env is not None:
            self.resource = simpy.Resource(self.env, capacity=1)
    
    def get_queue_length(self) -> int:
        """Return current cloud queue length"""
        return len(self.ntb_queue)
    
    def get_load(self) -> float:
        """Return current load percentage (0-1)"""
        return min(1.0, self.get_queue_length() / 50.0)  # Saturates at 50 tasks
    
    def enqueue_task(self, task):
        """Add task to cloud queue"""
        self.ntb_queue.append(task)
        self.load = self.get_load()
        return True
    
    def process_task(self, task):
        """
        SimPy process to execute a boulder task on cloud.
        
        Execution flow:
        1. Network latency (WAN roundtrip)
        2. Task processing based on MI and MIPS
        3. Return result to vehicle
        """
        if self.env is None:
            raise RuntimeError("Cloud server not initialized with SimPy environment")
        
        # Callback for execution start
        if task.get('on_execution_start'):
            task['on_execution_start'](task, 'cloud', self.env.now)
        
        # Check if task in queue
        if task in self.ntb_queue:
            self.ntb_queue.remove(task)
            self.load = self.get_load()
        
        try:
            # Phase 1: Transmission to cloud (WAN latency)
            transmission_latency = self.wan_latency_ms / 1000.0  # Convert to seconds
            yield self.env.timeout(transmission_latency)
            task['transmission_time'] = transmission_latency
            
            # Phase 2: Processing
            # Calculate processing time based on task MI (Million Instructions)
            total_mi = sum(step['MI'] for step in task.get('steps', {}).values() 
                          if step.get('MI'))
            
            # Avoid division by zero
            if total_mi > 0:
                processing_time = total_mi / (self.mips * 1e6)  # Convert to seconds
            else:
                processing_time = 0.01  # Minimum 10ms
            
            # Acquire cloud resource (single processor)
            with self.resource.request() as req:
                yield req
                
                # Execute task
                yield self.env.timeout(processing_time)
                task['execution_time'] = processing_time
                task['execution_device'] = 'cloud'
            
            # Phase 3: Result transmission back (WAN latency)
            result_transmission = (self.wan_latency_ms / 2) / 1000.0  # One-way
            yield self.env.timeout(result_transmission)
            task['result_transmission_time'] = result_transmission
            
            # Task completed successfully
            task['completed'] = True
            task['completion_time'] = self.env.now
            
            # Calculate total latency (from task generation to completion)
            total_latency = task['completion_time'] - task.get('created_at', 0)
            task['total_latency_ms'] = total_latency * 1000
            
            # Check deadline
            deadline = task.get('deadline_ms', 200)
            task['deadline_met'] = (task['total_latency_ms'] <= deadline)
            
            # Update metrics
            self.processed_tasks += 1
            self.total_processing_time += processing_time
            
            # Callback for completion
            if task.get('on_completion'):
                task['on_completion'](task, 'cloud', self.env.now)
        
        except Exception as e:
            # Task failed
            task['completed'] = False
            task['error'] = str(e)
            task['completion_time'] = self.env.now
            
            if task.get('on_failure'):
                task['on_failure'](task, 'cloud', self.env.now, str(e))
    
    def add_processing_process(self, task):
        """Add a new task processing process to the simulation"""
        if self.env is None:
            raise RuntimeError("Cloud server not initialized with SimPy environment")
        
        self.env.process(self.process_task(task))
    
    def get_status(self) -> Dict:
        """Return current cloud server status"""
        return {
            'name': self.name,
            'mips': self.mips,
            'queue_length': self.get_queue_length(),
            'load': self.get_load(),
            'processed_tasks': self.processed_tasks,
            'avg_processing_time': (
                self.total_processing_time / self.processed_tasks 
                if self.processed_tasks > 0 else 0
            ),
        }
