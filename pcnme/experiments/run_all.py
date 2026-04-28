"""
PCNME Main Simulation Runner
Executes all 6 systems × 5 seeds × 3 scenarios = 90 runs.

Usage:
    python experiments/run_all.py \\
        --output experiments/results/raw_results.csv \\
        --weights experiments/weights/ \\
        --systems proposed greedy dqn_cold
"""

import argparse
import numpy as np
from pathlib import Path
from datetime import datetime
import sys
from typing import Optional

# Add parent directory to path (dslab2 root)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pcnme import (
    TaskRecord, MetricsCollector,
    DataManager, SimulationEnvironment, create_system,
    DQNAgent, SEEDS, SCENARIO_SPEEDS,
    N_VEHICLES, SIM_DURATION_S, WARMUP_S, DAG, TOTAL_DEADLINE_MS
)
from pcnme.progress import progress
from pcnme.utilities import setup_logging, get_logger


class PCNMESimulator:
    """
    Main PCNME simulator orchestrating task execution.
    """

    def __init__(self, env: SimulationEnvironment, system, data_manager: DataManager, system_name: str = None, logger=None):
        self.env = env
        self.system = system
        self.data_manager = data_manager
        self.system_name = system_name or system.__class__.__name__
        self.metrics_collector = MetricsCollector()
        self.logger = logger or logging.getLogger('PCNME.RunAll')

    def run_single_task(self, vehicle_id: str, task_id: str,
                       scenario: str, seed: int, sim_time_s: float = 0.0):
        """
        Execute a single task (all 5 DAG steps) for a vehicle.

        Returns:
            TaskRecord with complete results
        """
        # Get vehicle state at current time
        vehicle = self.env.vehicles.get(vehicle_id)
        if not vehicle or not vehicle.is_active(sim_time_s):
            return None

        # Get fog state
        fog_state = self.env.get_fog_state()

        # Initialize results
        results = {
            'task_id': task_id,
            'system': self.system_name,
            'seed': seed,
            'scenario': scenario,
            'vehicle_id': vehicle_id,
            'sim_time_s': sim_time_s,
            'step2_latency_ms': 0.0,
            'step3_latency_ms': 0.0,
            'step4_latency_ms': 0.0,
            'step5_latency_ms': 0.0,
            'step2_energy_j': 0.0,
            'step3_energy_j': 0.0,
            'step4_energy_j': 0.0,
            'step5_energy_j': 0.0,
            'step2_dest': None,
            'step3_dest': None,
            'step5_dest': None,
            'n_boulders': 2,  # steps 3, 4
            'n_pebbles': 2,   # steps 2, 5
            'handoff_occurred': False,
            'handoff_mode': 'none',
            'handoff_success': False,
            't_exit_at_decision': 0.0,
            'fog_A_load': 0.0,
            'fog_B_load': 0.0,
            'fog_C_load': 0.0,
            'fog_D_load': 0.0,
            'fog_A_queue': 0,
            'fog_B_queue': 0,
            'fog_C_queue': 0,
            'fog_D_queue': 0,
            'agent_q_max': None,
            'agent_epsilon': None,
            'agent_reward': None,
            'bc_loss_final': None,
            'online_updates': None,
        }

        total_latency = 0.0
        total_energy = 0.0

        # Execute each step
        for step_id in [2, 3, 4, 5]:
            step_mi = DAG[step_id]['MI']
            step_data = DAG[step_id]['in_KB']  # Input data for this step
            
            # Select destination using system's policy
            destination = self.system.select_destination(
                vehicle_id, step_id, step_mi, sim_time_s
            )

            # Execute task
            if destination == 'cloud':
                latency, energy = self.env.execute_task_on_cloud(
                    step_mi, step_data, vehicle_id, sim_time_s
                )
            else:
                latency, energy = self.env.execute_task_on_fog(
                    step_mi, step_data, destination, vehicle_id, sim_time_s
                )

            results[f'step{step_id}_latency_ms'] = latency
            results[f'step{step_id}_energy_j'] = energy
            if step_id != 4:  # Don't record step 4 destination
                results[f'step{step_id}_dest'] = destination

            total_latency += latency
            total_energy += energy

        # Add step 1 (device): simplified model
        step1_mi = DAG[1]['MI']
        step1_latency = step1_mi / 3000.0 * 1000  # ~7ms on device
        step1_energy = 0.001  # negligible
        total_latency += step1_latency
        total_energy += step1_energy

        results['total_latency_ms'] = total_latency
        results['total_energy_j'] = total_energy
        results['deadline_met'] = total_latency <= TOTAL_DEADLINE_MS

        # Extract fog loads and queues from fog_state
        for node_name in ['A', 'B', 'C', 'D']:
            results[f'fog_{node_name}_load'] = fog_state[node_name]['load']
            results[f'fog_{node_name}_queue'] = fog_state[node_name]['queue']

        # Check handoff conditions
        t_exit_a = self.env.compute_t_exit_to_fog(vehicle_id, 'A', sim_time_s)
        results['t_exit_at_decision'] = t_exit_a
        results['handoff_occurred'] = t_exit_a < 10.0  # simplified
        if results['handoff_occurred']:
            results['handoff_success'] = np.random.rand() > 0.1  # 90% success
            results['handoff_mode'] = 'proactive' if t_exit_a < 5.0 else 'direct'

        # Create record
        record = TaskRecord(**results)
        return record

    def run_scenario(self, scenario: str, seed: int, n_vehicles: Optional[int] = None):
        """
        Run complete simulation for one scenario.

        Args:
            scenario: 'morning_rush', 'off_peak', or 'evening_rush'
            seed: random seed
            n_vehicles: number of vehicles (default: use constant)

        Returns:
            list of TaskRecords
        """
        if n_vehicles is None:
            n_vehicles = N_VEHICLES

        self.logger.debug(f"  Loading traces for {scenario}...")
        traces = self.data_manager.get_traces(
            scenario, n_vehicles=n_vehicles, seed=seed
        )

        self.logger.debug(f"  Initializing {len(traces)} vehicles...")
        # Add vehicles to environment
        from pcnme import Vehicle
        for trace in traces:
            vehicle = Vehicle(trace['vehicle_id'], trace['xs'], trace['ys'], 
                            trace['speeds'], trace['headings'], trace['timestamps'])
            self.env.add_vehicle(vehicle)

        task_records = []
        task_counter = 0

        # Simulation loop (generate tasks at fixed time points)
        self.logger.debug(f"  Running simulation (duration: {SIM_DURATION_S}s)...")
        n_steps = int(SIM_DURATION_S)
        pbar = progress(total=n_steps, desc=f"{scenario} seed={seed}", 
                       unit="s", leave=False)
        
        try:
            for sim_time_s in range(int(WARMUP_S), int(SIM_DURATION_S), 1):
                # Skip warmup period
                if sim_time_s < WARMUP_S:
                    pbar.update(1)
                    continue
                
                # Generate one task per active vehicle per 10 seconds
                if sim_time_s % 10 == 0:
                    for vehicle_id in list(self.env.vehicles.keys()):
                        # Check if vehicle is active at this time
                        vehicle = self.env.vehicles[vehicle_id]
                        if vehicle.is_active(sim_time_s):
                            task_id = f"{scenario}_{seed}_{vehicle_id}_{task_counter}"
                            record = self.run_single_task(
                                vehicle_id, task_id, scenario, seed, sim_time_s
                            )
                            if record:
                                task_records.append(record)
                                task_counter += 1

                # Update fog loads
                self.env.update_fog_loads(dt_s=1.0)
                pbar.update(1)
        finally:
            pbar.close()

        self.logger.info(f"  [OK] Completed: {len(task_records)} task records")
        return task_records


def main():
    parser = argparse.ArgumentParser(
        description="PCNME Full Simulation Suite"
    )
    parser.add_argument('--output', type=Path,
                       default=Path(__file__).parent / 'results' / 'raw_results.csv',
                       help='Output CSV file for results')
    parser.add_argument('--weights', type=Path, default=Path(__file__).parent / 'weights',
                       help='Directory containing pre-trained weights')
    parser.add_argument('--systems', nargs='+',
                       default=['random', 'greedy', 'nsga2_static',
                               'dqn_cold', 'dqn_bc_only', 'proposed'],
                       help='Systems to run')
    parser.add_argument('--scenarios', nargs='+',
                       default=['morning_rush', 'off_peak', 'evening_rush'],
                       help='Scenarios to run')
    parser.add_argument('--n-vehicles', type=int, default=N_VEHICLES,
                       help='Number of vehicles per scenario')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING'], default='INFO',
                       help='Logging level')

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.output.parent / 'logs', 'run_all', args.log_level)
    
    print("=" * 70)
    print("PCNME FULL SIMULATION SUITE")
    print("=" * 70)
    logger.info("=" * 70)
    logger.info("PCNME FULL SIMULATION SUITE")
    logger.info("=" * 70)
    
    print(f"Systems: {args.systems}")
    print(f"Scenarios: {args.scenarios}")
    print(f"Seeds: {SEEDS}")
    print(f"Total runs: {len(args.systems)} × {len(args.scenarios)} × {len(SEEDS)}")
    print("=" * 70 + "\n")
    
    logger.info(f"Systems: {args.systems}")
    logger.info(f"Scenarios: {args.scenarios}")
    logger.info(f"Seeds: {SEEDS}")
    logger.info(f"Total runs: {len(args.systems)} × {len(args.scenarios)} × {len(SEEDS)}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Weights dir: {args.weights}")

    data_manager = DataManager()
    metrics_collector = MetricsCollector()

    total_tasks = len(args.systems) * len(args.scenarios) * len(SEEDS)
    completed_tasks = 0

    runs_pbar = progress(total=total_tasks, desc="All runs", unit="run")

    start_time = datetime.now()
    logger.info(f"Simulation started at {start_time}")

    # Loop: systems × scenarios × seeds
    for system_name in args.systems:
        print(f"\n[SYSTEM: {system_name}]")
        logger.info(f"[SYSTEM: {system_name}]")

        # Load DQN if needed
        dqn_agent = None
        if system_name in ['dqn_cold', 'dqn_bc_only', 'proposed']:
            from pcnme import DQNAgent, STATE_DIM, ACTION_DIM, HIDDEN
            dqn_agent = DQNAgent(STATE_DIM, ACTION_DIM, HIDDEN)

            weights_file = args.weights / 'dqn_bc_pretrained.pt'
            if weights_file.exists():
                logger.info(f"  Loading pre-trained weights from {weights_file}")
                dqn_agent.load_weights(weights_file)
            else:
                logger.warning(f"  Weights file not found: {weights_file}")

        for scenario in args.scenarios:
            print(f"  [{scenario}]")
            logger.info(f"  [{scenario}]")

            for seed in SEEDS:
                print(f"    Seed {seed}...", end='', flush=True)

                # Set random seed
                np.random.seed(seed)

                # Create environment and system
                env = SimulationEnvironment()
                system = create_system(system_name, env, dqn_agent, seed=seed)

                # Run simulator
                simulator = PCNMESimulator(env, system, data_manager, system_name, logger=logger)
                task_records = simulator.run_scenario(scenario, seed,
                                                      args.n_vehicles)

                # Collect metrics
                for record in task_records:
                    metrics_collector.add_record(record)

                completed_tasks += 1
                runs_pbar.update(1)
                elapsed = (datetime.now() - start_time).total_seconds()
                msg = f" {len(task_records)} tasks | {completed_tasks}/{total_tasks} | Elapsed: {elapsed/60:.1f}m"
                print(msg)
                logger.debug(msg)

    runs_pbar.close()

    # Save results
    print(f"\nSaving {len(metrics_collector.records)} records to {args.output}")
    logger.info(f"Saving {len(metrics_collector.records)} records to {args.output}")
    metrics_collector.save_csv(args.output)

    elapsed_total = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 70)
    print("SIMULATION COMPLETE")
    print("=" * 70)
    print(f"Total time: {elapsed_total / 60:.1f} minutes")
    print(f"Output: {args.output}")
    
    logger.info("=" * 70)
    logger.info("SIMULATION COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total time: {elapsed_total / 60:.1f} minutes")
    logger.info(f"Output: {args.output}")


if __name__ == '__main__':
    main()
