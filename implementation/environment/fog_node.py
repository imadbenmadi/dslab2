import simpy
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class FogNode:
    """Fog compute node with task queue management."""
    node_id: str
    position: tuple
    mips: int
    env: simpy.Environment
    ntb_queue: List = field(default_factory=list)  # Normal Task Buffer
    htb_queue: List = field(default_factory=list)  # Handoff Task Buffer
    
    def __post_init__(self):
        self.resource = simpy.Resource(self.env, capacity=1)
        self.load = 0.0
    
    def process_task(self, task):
        """Process a task on this fog node"""
        pass
    
    def get_queue_length(self):
        """Return current queue length"""
        return len(self.ntb_queue) + len(self.htb_queue)
