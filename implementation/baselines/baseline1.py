"""
Baseline 1: Pure NSGA-II (Offline Optimization Only)

Offline generates Pareto-optimal task placements with NSGA-II,
then applies them statically throughout simulation with NO online adaptation.

Expected Performance (from thesis definition):
- Deadline Success: ~47%
- Avg Latency: ~167.2 ms  
- Avg Energy: ~0.250 J
- Handoff Success: ~51%
"""

import sys
import numpy as np
from typing import List, Dict, Any, Tuple
from datetime import datetime
from simpy import Environment as SimEnvironment
from collections import defaultdict

from config import (
    N_VEHICLES, SIM_DURATION_S, TASK_RATE_HZ, RANDOM_SEED,
    FOG_MIPS, CLOUD_MIPS, FOG_NODES, BANDWIDTH_MBPS, WAN_LATENCY_MS,
    G5_LATENCY_MS, TOTAL_DEADLINE_MS, N_OFFLINE_BATCHES, NSGA_POP_SIZE, NSGA_GENS
)
from environment.task import Task
from environment.vehicle import Vehicle
from optimizer.nsga2_mmde import run_nsga2_mmde
from results.baseline_results import get_baseline_tracker


class Baseline1Simulator:
    """Pure NSGA-II baseline: optimize once, apply statically."""

    def __init__(self, seed: int = RANDOM_SEED):
        self.seed = seed
        np.random.seed(seed)
        self.env = SimEnvironment()
        self.vehicles: Dict[str, Vehicle] = {}
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
        self.pareto_decisions = {}  # Cached NSGA-II decisions
        self.tracker = get_baseline_tracker()

    def bootstrap_nsga2(self) -> Dict[str, Any]:
        """Run offline NSGA-II once at startup."""
        print(f"[Baseline1] Running offline NSGA-II (pop={NSGA_POP_SIZE}, gen={NSGA_GENS})...")
        
        # Generate mock bootstrap tasks for optimization
        bootstrap_tasks = [Task(f"boot_{i}", 50, 100) for i in range(min(100, N_OFFLINE_BATCHES))]
        fog_states = {fid: 0.3 for fid in FOG_NODES}  # Initial fog loads (30% busy)
        
        try:
            result = run_nsga2_mmde(
                bootstrap_tasks=bootstrap_tasks,
                fog_states=fog_states,
                pop_size=NSGA_POP_SIZE,
                n_gens=NSGA_GENS,
                method="nsga2",  # Pure NSGA-II, no MMDE
                timeout_s=30.0
            )
            print(f"[Baseline1] NSGA-II complete: {len(result.get('pareto_X', []))} Pareto solutions")
            return result
        except Exception as e:
            print(f"[Baseline1] NSGA-II failed: {e}")
            return {"pareto_X": [], "pareto_F": [], "knee_X": [], "knee_F": None}

    def place_task_static(self, task: Task, pareto_decisions: Dict[str, Any]) -> str:
        """Apply cached NSGA-II decision (static placement, no adaptation)."""
        if not pareto_decisions.get("knee_X") is not None:
            # Fallback: send to least-loaded fog
            fog_loads = defaultdict(lambda: 999)
            fog_loads.update({fid: 0.3 for fid in FOG_NODES})  
            best_fog = min(fog_loads, key=fog_loads.get)
            return best_fog

        # Get decision from cached Pareto front
        decision_idx = int(task.task_id.split('_')[-1]) % len(pareto_decisions.get("knee_X", [1]))
        decision = pareto_decisions["knee_X"][decision_idx] if len(pareto_decisions.get("knee_X", [])) > 0 else 0
        
        # Map decision to placement
        placement_map = {0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'CLOUD'}
        return placement_map.get(int(decision), 'A')

    def simulate_task_execution(self, task: Task, destination: str) -> Tuple[float, float, bool]:
        """Simulate task execution at destination node and compute latency + energy."""
        
        # Transmission latency (always required)
        tx_latency_ms = (task.input_size_kb * 8) / (BANDWIDTH_MBPS * 1000) * 1000 + G5_LATENCY_MS
        tx_energy = (task.input_size_kb / 1024) * 0.05  # 0.05J per GB
        
        if destination == 'CLOUD':
            # Cloud execution: longer path
            exec_latency_ms = (task.mi / CLOUD_MIPS) * 1000
            total_latency_ms = tx_latency_ms + WAN_LATENCY_MS + exec_latency_ms
            exec_energy = 0.0001 * task.mi / 1000  # Higher cloud energy estimation
            total_energy = tx_energy + exec_energy
        else:
            # Fog execution
            exec_latency_ms = (task.mi / FOG_MIPS) * 1000
            total_latency_ms = tx_latency_ms + exec_latency_ms
            exec_energy = 0.00005 * task.mi / 1000
            total_energy = tx_energy + exec_energy
        
        # Check deadline
        deadline_met = total_latency_ms <= TOTAL_DEADLINE_MS
        
        return total_latency_ms, total_energy, deadline_met

    def run(self, duration_s: float = SIM_DURATION_S) -> Dict[str, Any]:
        """Run pure NSGA-II baseline simulation."""
        
        print(f"\n{'='*70}")
        print(f"BASELINE 1: Pure NSGA-II (Offline Optimization Only)")
        print(f"Duration: {duration_s}s | Vehicles: {N_VEHICLES} | Fog Nodes: {len(FOG_NODES)}")
        print(f"{'='*70}\n")
        
        # Phase 1: Offline optimization
        start_time = datetime.now()
        pareto_result = self.bootstrap_nsga2()
        
        # Phase 2: Static simulation using cached decisions
        self.tracker.start_run("baseline1")
        
        task_id_counter = 0
        task_generation_rate = TASK_RATE_HZ
        sim_time = 0.0
        
        while sim_time < duration_s:
            # Generate tasks at fixed rate
            num_new_tasks = int(task_generation_rate)
            for _ in range(num_new_tasks):
                task = Task(
                    task_id=f"task_{task_id_counter}",
                    mi=np.random.randint(50, 500),
                    input_size_kb=np.random.randint(50, 200)
                )
                task_id_counter += 1
                
                # Apply static NSGA-II decision
                destination = self.place_task_static(task, pareto_result)
                
                # Simulate execution
                latency_ms, energy_j, deadline_met = self.simulate_task_execution(task, destination)
                
                # Record metrics
                self.tracker.record_task_completion(latency_ms, energy_j, deadline_met, destination)
                self.completed_tasks.append(task)
            
            sim_time += 1.0
        
        # Finalize
        final_metrics = self.tracker.finalize_run(duration_s)
        
        print(f"\n{'='*70}")
        print("BASELINE 1 FINAL RESULTS:")
        print(f"{'='*70}")
        print(f"Tasks Total:           {final_metrics.get('tasks_total', 0)}")
        print(f"Deadline Success:      {final_metrics.get('success_rate', 0):.1f}%")
        print(f"Avg Latency:           {final_metrics.get('avg_latency_ms', 0):.1f} ms")
        print(f"Avg Energy:            {final_metrics.get('avg_energy_j', 0):.4f} J")
        print(f"Local Exec:            {final_metrics.get('local_exec', 0)}")
        print(f"Fog Exec:              {final_metrics.get('fog_exec', 0)}")
        print(f"Cloud Exec:            {final_metrics.get('cloud_exec', 0)}")
        print(f"Handoffs:              {final_metrics.get('handoff_count', 0)}")
        print(f"Duration:              {(datetime.now() - start_time).total_seconds():.1f}s")
        print(f"{'='*70}\n")
        
        return final_metrics


if __name__ == "__main__":
    sim = Baseline1Simulator(seed=RANDOM_SEED)
    results = sim.run(duration_s=SIM_DURATION_S)
    sys.exit(0 if results else 1)
