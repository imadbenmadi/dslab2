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

sys.path.insert(0, str(Path(__file__).parent.parent))

from pcnme import (
    TaskRecord, MetricsCollector,
    DataManager, SimulationEnvironment, create_system,
    DQNAgent, SEEDS, SCENARIO_SPEEDS,
    N_VEHICLES, SIM_DURATION_S, WARMUP_S, DAG
)


class PCNMESimulator:
    """
    Main PCNME simulator orchestrating task execution.
    """

    def __init__(self, env: SimulationEnvironment, system, data_manager: DataManager):
        self.env = env
        self.system = system
        self.data_manager = data_manager
        self.metrics_collector = MetricsCollector()

    def run_single_task(self, vehicle_id: str, task_id: str,
                       scenario: str, seed: int):
        """
        Execute a single task (all 5 DAG steps) for a vehicle.

        Returns:
            TaskRecord with complete results
        """
        # Get vehicle state at current time
        vehicle_state = self.env.get_vehicle_state(vehicle_id)
        if not vehicle_state or not vehicle_state['is_active']:
            return None

        # Get fog state
        fog_state = self.env.get_fog_state()

        # Initialize results
        results = {
            'task_id': task_id,
            'system': self.system.system_name,
            'seed': seed,
            'scenario': scenario,
            'vehicle_id': vehicle_id,
            'sim_time_s': self.env.sim_time_s,
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
            'fog_A_load': fog_state['loads']['A'],
            'fog_B_load': fog_state['loads']['B'],
            'fog_C_load': fog_state['loads']['C'],
            'fog_D_load': fog_state['loads']['D'],
            'fog_A_queue': fog_state['queues']['A'],
            'fog_B_queue': fog_state['queues']['B'],
            'fog_C_queue': fog_state['queues']['C'],
            'fog_D_queue': fog_state['queues']['D'],
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
            # Skip step 1 (always device-local) and step 4 (always cloud, not recorded)
            if step_id == 1:
                continue
            
            # Step 4 is boulder - execute it but don't record destination decision
            if step_id == 4:
                destination = 'cloud'
                exec_result = self.env.execute_task(
                    task_id, step_id, destination, vehicle_id
                )
                results[f'step{step_id}_latency_ms'] = exec_result['latency_ms']
                results[f'step{step_id}_energy_j'] = exec_result['energy_j']
                total_latency += exec_result['latency_ms']
                total_energy += exec_result['energy_j']
                continue

            # Select destination for pebbles/boulders with decisions (steps 2, 3, 5)
            destination = self.system.select_destination(
                step_id, vehicle_id, fog_state
            )

            # Execute step
            exec_result = self.env.execute_task(
                task_id, step_id, destination, vehicle_id
            )

            latency = exec_result['latency_ms']
            energy = exec_result['energy_j']

            results[f'step{step_id}_latency_ms'] = latency
            results[f'step{step_id}_energy_j'] = energy
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
        results['deadline_met'] = total_latency <= 200.0

        # Check handoff conditions
        t_exit_a = self.env.compute_t_exit_to_fog(vehicle_id, 'A')
        results['t_exit_at_decision'] = t_exit_a
        results['handoff_occurred'] = t_exit_a < 10.0  # simplified
        if results['handoff_occurred']:
            results['handoff_success'] = np.random.rand() > 0.1  # 90% success
            results['handoff_mode'] = 'proactive' if t_exit_a < 5.0 else 'direct'

        # Create record
        record = TaskRecord(**results)
        return record

    def run_scenario(self, scenario: str, seed: int, n_vehicles: int = None):
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

        print(f"  Loading traces for {scenario}...")
        traces = self.data_manager.get_traces(
            scenario, n_vehicles=n_vehicles, seed=seed
        )

        print(f"  Initializing {len(traces)} vehicles...")
        self.env.initialize(traces)

        task_records = []
        task_counter = 0

        # Simulation loop
        print(f"  Running simulation (duration: {SIM_DURATION_S}s)...")
        while self.env.sim_time_s < SIM_DURATION_S:
            # Generate tasks for active vehicles
            for vehicle_id in self.env.vehicles:
                # One task per vehicle per 10 seconds
                if int(self.env.sim_time_s) % 10 == 0:
                    task_id = f"{scenario}_{seed}_{vehicle_id}_{task_counter}"

                    record = self.run_single_task(
                        vehicle_id, task_id, scenario, seed
                    )

                    if record:
                        task_records.append(record)
                        task_counter += 1

            # Step environment
            self.env.step()

            # Progress
            if int(self.env.sim_time_s) % 60 == 0:
                print(f"    {self.env.sim_time_s:.0f}s / {SIM_DURATION_S}s "
                      f"({task_counter} tasks)")

        print(f"  ✓ Completed: {len(task_records)} task records")
        return task_records


def main():
    parser = argparse.ArgumentParser(
        description="PCNME Full Simulation Suite"
    )
    parser.add_argument('--output', type=Path,
                       default='experiments/results/raw_results.csv',
                       help='Output CSV file for results')
    parser.add_argument('--weights', type=Path, default='experiments/weights/',
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

    args = parser.parse_args()

    print("=" * 70)
    print("PCNME FULL SIMULATION SUITE")
    print("=" * 70)
    print(f"Systems: {args.systems}")
    print(f"Scenarios: {args.scenarios}")
    print(f"Seeds: {SEEDS}")
    print(f"Total runs: {len(args.systems)} × {len(args.scenarios)} × {len(SEEDS)}")
    print("=" * 70 + "\n")

    data_manager = DataManager()
    metrics_collector = MetricsCollector()

    total_tasks = len(args.systems) * len(args.scenarios) * len(SEEDS)
    completed_tasks = 0

    start_time = datetime.now()

    # Loop: systems × scenarios × seeds
    for system_name in args.systems:
        print(f"\n[SYSTEM: {system_name}]")

        # Load DQN if needed
        dqn_agent = None
        if system_name in ['dqn_cold', 'dqn_bc_only', 'proposed']:
            from pcnme import DQNAgent, STATE_DIM, ACTION_DIM, HIDDEN
            dqn_agent = DQNAgent(STATE_DIM, ACTION_DIM, HIDDEN)

            weights_file = args.weights / 'dqn_bc_pretrained.pt'
            if weights_file.exists():
                print(f"  Loading pre-trained weights from {weights_file}")
                dqn_agent.load_weights(weights_file)
            else:
                print(f"  ⚠ Weights file not found: {weights_file}")

        for scenario in args.scenarios:
            print(f"  [{scenario}]")

            for seed in SEEDS:
                print(f"    Seed {seed}...", end='', flush=True)

                # Create environment and system
                env = SimulationEnvironment(seed=seed)
                system = create_system(system_name, env, dqn_agent, seed=seed)

                # Run simulator
                simulator = PCNMESimulator(env, system, data_manager)
                task_records = simulator.run_scenario(scenario, seed,
                                                      args.n_vehicles)

                # Collect metrics
                for record in task_records:
                    metrics_collector.add_record(record)

                completed_tasks += 1
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f" {len(task_records)} tasks | "
                      f"{completed_tasks}/{total_tasks} | "
                      f"Elapsed: {elapsed/60:.1f}m")

    # Save results
    print(f"\nSaving {len(metrics_collector.records)} records to {args.output}")
    metrics_collector.save_csv(args.output)

    print("\n" + "=" * 70)
    print("SIMULATION COMPLETE")
    print("=" * 70)
    print(f"Total time: {(datetime.now() - start_time).total_seconds() / 60:.1f} minutes")
    print(f"Output: {args.output}")


if __name__ == '__main__':
    main()
