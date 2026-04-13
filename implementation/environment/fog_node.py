"""
Complete Fog Node Implementation
Processes pebble-class tasks with queue management and handoff support
"""

import simpy
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from config import FOG_MIPS, BANDWIDTH_MBPS


@dataclass
class FogNode:
    """
    Fog compute node with task queue management.
    
    Queues:
    - NTB (Normal Task Buffer): Standard tasks from vehicles in coverage
    - HTB (Handoff Task Buffer): Tasks from vehicles leaving coverage
    """
    node_id: str
    position: tuple
    mips: int = FOG_MIPS  # 2000 MIPS per fog node
    env: Optional[simpy.Environment] = None
    
    # Queues
    ntb_queue: List = field(default_factory=list)  # Normal Task Buffer
    htb_queue: List = field(default_factory=list)  # Handoff Task Buffer
    
    # Network parameters
    uplink_bandwidth_mbps: float = BANDWIDTH_MBPS  # 100 Mbps to/from vehicles
    
    # Metrics
    processed_tasks: int = 0
    total_processing_time: float = 0.0
    task_completion_callback: Optional[Callable] = None
    
    def __post_init__(self):
        if self.env is not None:
            self.resource = simpy.Resource(self.env, capacity=1)
            self.load = 0.0
    
    def get_queue_length(self) -> int:
        """Return total queue length (NTB + HTB)"""
        return len(self.ntb_queue) + len(self.htb_queue)
    
    def get_load(self) -> float:
        """Return current load percentage (0-1)"""
        return min(1.0, self.get_queue_length() / 30.0)  # Saturates at 30 tasks
    
    def enqueue_task(self, task, buffer_type: str = 'ntb'):
        """
        Add task to appropriate queue.
        
        Args:
            task: Task dict to process
            buffer_type: 'ntb' (normal) or 'htb' (handoff)
        """
        if buffer_type == 'ntb':
            self.ntb_queue.append(task)
        elif buffer_type == 'htb':
            self.htb_queue.append(task)
        else:
            raise ValueError(f"Invalid buffer type: {buffer_type}")
        
        self.load = self.get_load()
        return True
    
    def calculate_transmission_time(self, data_size_kb: float) -> float:
        """
        Calculate transmission time for data.
        
        Args:
            data_size_kb: Data size in kilobytes
            
        Returns:
            Time in seconds
        """
        if self.uplink_bandwidth_mbps <= 0:
            return 0
        
        # Convert: KB to Mb, then divide by Mbps to get seconds
        data_size_mb = data_size_kb / 1024
        transmission_time = (data_size_mb * 8) / self.uplink_bandwidth_mbps
        
        return transmission_time
    
    def process_task(self, task, buffer_type: str = 'ntb'):
        """
        SimPy process to execute a pebble task on fog node.
        
        Execution flow:
        1. Transmission input data to fog (network latency)
        2. Task processing based on MI and MIPS
        3. Transmission output data back to vehicle
        
        Args:
            task: Task dict with MI, input/output sizes
            buffer_type: Queue type ('ntb' or 'htb')
        """
        if self.env is None:
            raise RuntimeError("Fog node not initialized with SimPy environment")
        
        # Callback for execution start
        if task.get('on_execution_start'):
            task['on_execution_start'](task, f'fog-{self.node_id}', self.env.now)
        
        # Remove from queue
        try:
            if buffer_type == 'ntb' and task in self.ntb_queue:
                self.ntb_queue.remove(task)
            elif buffer_type == 'htb' and task in self.htb_queue:
                self.htb_queue.remove(task)
            self.load = self.get_load()
        except ValueError:
            pass
        
        try:
            # Phase 1: Input transmission (vehicle → fog)
            input_size_kb = task.get('input_size_kb', 200)
            input_transmission_time = self.calculate_transmission_time(input_size_kb)
            yield self.env.timeout(input_transmission_time)
            task['input_transmission_time'] = input_transmission_time
            
            # Phase 2: Processing
            # Get total MI from task steps
            total_mi = sum(step.get('MI', 0) for step in task.get('steps', {}).values())
            
            if total_mi > 0:
                processing_time = total_mi / (self.mips * 1e6)  # Convert to seconds
            else:
                processing_time = 0.01  # Minimum 10ms
            
            # Acquire fog resource (single core per node)
            with self.resource.request() as req:
                yield req
                
                # Execute task
                yield self.env.timeout(processing_time)
                task['execution_time'] = processing_time
                task['execution_device'] = f'fog-{self.node_id}'
            
            # Phase 3: Output transmission (fog → vehicle)
            output_size_kb = task.get('output_size_kb', 50)
            output_transmission_time = self.calculate_transmission_time(output_size_kb)
            yield self.env.timeout(output_transmission_time)
            task['output_transmission_time'] = output_transmission_time
            
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
                task['on_completion'](task, f'fog-{self.node_id}', self.env.now)
        
        except Exception as e:
            # Task failed or preempted
            task['completed'] = False
            task['error'] = str(e)
            task['completion_time'] = self.env.now
            
            if task.get('on_failure'):
                task['on_failure'](task, f'fog-{self.node_id}', self.env.now, str(e))
    
    def add_processing_process(self, task, buffer_type: str = 'ntb'):
        """Add a new task processing process to the simulation"""
        if self.env is None:
            raise RuntimeError("Fog node not initialized with SimPy environment")
        
        self.env.process(self.process_task(task, buffer_type))
    
    def get_status(self) -> Dict:
        """Return current fog node status"""
        return {
            'node_id': self.node_id,
            'position': self.position,
            'mips': self.mips,
            'ntb_queue_length': len(self.ntb_queue),
            'htb_queue_length': len(self.htb_queue),
            'total_queue_length': self.get_queue_length(),
            'load': self.get_load(),
            'processed_tasks': self.processed_tasks,
            'avg_processing_time': (
                self.total_processing_time / self.processed_tasks 
                if self.processed_tasks > 0 else 0
            ),
        }
