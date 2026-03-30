from dataclasses import dataclass, field
from typing import List

@dataclass
class CloudServer:
    """Central cloud server for task processing."""
    name: str = "Cloud"
    mips: int = 8000
    queue: List = field(default_factory=list)
    load: float = 0.0
    
    def process_task(self, task):
        """Process a boulder task on cloud"""
        pass
    
    def get_queue_length(self):
        """Return current cloud queue length"""
        return len(self.queue)
