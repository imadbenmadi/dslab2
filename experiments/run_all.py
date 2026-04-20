"""
Main simulation script: run all systems × seeds × scenarios.
"""

import argparse
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from pcnme import (
    SYSTEMS, SCENARIOS, SEEDS, N_VEHICLES, SIM_DURATION_S, WARMUP_S, DAG,
    SimulationEnvironment, Vehicle, DataManager, create_system,
    MetricsCollector, TaskRecord,
    classify_step, step_latency, step_energy, compute_t_exit, build_state
)


def _resolve_repo_relative(path_str: str, repo_root: Path) -> Path:
    """Resolve a path relative to the repo root (not the current working dir)."""
    path = Path(path_str)
    return path if path.is_absolute() else (repo_root / path).resolve()


def _find_weights_file(weights_dir: Path, repo_root: Path) -> Path:
    """Find the DQN pretrained weights file, with a fallback to pcnme/experiments."""
    candidate = weights_dir / "dqn_bc_pretrained.pt"
    if candidate.exists():
        return candidate

    fallback = repo_root / "pcnme" / "experiments" / "weights" / "dqn_bc_pretrained.pt"
    if fallback.exists():
        return fallback

    raise FileNotFoundError(
        "Pretrained weights not found. Expected one of:\n"
        f"- {candidate}\n"
        f"- {fallback}\n\n"
        "Run `python experiments/pretrain.py` (repo root) or "
        "`python pcnme/experiments/pretrain.py` to generate the weights, "
        "or pass `--weights` pointing to the directory containing dqn_bc_pretrained.pt."
    )


def run_simulation(system_type: str, scenario: str, seed: int, n_vehicles: int,
                  weights_path: Path = None) -> list:
    """Run one complete simulation."""
    # Initialize environment
    env = SimulationEnvironment()

    # Load traces
    dm = DataManager()
    traces = dm.get_traces(scenario, n_vehicles=n_vehicles, seed=seed)

    # Add vehicles
    for trace in traces[:n_vehicles]:
        vehicle = Vehicle(
            trace["vehicle_id"], trace["xs"], trace["ys"],
            trace["speeds"], trace["headings"], trace["timestamps"]
        )
        env.add_vehicle(vehicle)

    # Create system
    system = create_system(system_type, env, weights_path=weights_path, seed=seed)

    # Run simulation
    collector = MetricsCollector()
    task_counter = 0

    for sim_time in np.arange(WARMUP_S, SIM_DURATION_S, 1.0):
        for vehicle in env.vehicles.values():
            if not vehicle.is_active(sim_time):
                continue

            task_id = f"{system_type}_{scenario}_{seed}_{vehicle.vehicle_id}_{int(sim_time)}"
            vehicle_x, vehicle_y = vehicle.get_position_at_time(sim_time)
            vehicle_speed = vehicle.get_speed_at_time(sim_time)
            vehicle_heading = vehicle.get_heading_at_time(sim_time)

            # Execute task steps
            total_latency = 0.0
            total_energy = 0.0
            step_latencies = {}
            step_energies = {}
            step_dests = {}
            n_boulders = 0
            n_pebbles = 0
            deadline_met = True

            for step_id in [1, 2, 3, 4, 5]:
                step_info = DAG[step_id]
                step_MI = step_info["MI"]
                data_in_KB = step_info["in_KB"]

                if step_id == 1:
                    # Device execution (step 1)
                    dest = "device"
                    lat = data_in_KB * 8 / 100 + 5  # rough device latency
                    eng = 0.005
                else:
                    # Select destination
                    if classify_step(step_MI) == "boulder":
                        dest = "cloud"
                    else:
                        dest = system.select_destination(
                            vehicle.vehicle_id, step_id, step_MI, sim_time
                        )

                    # Compute latency and energy
                    fog_state = env.get_fog_state()
                    fog_load = min(0.5, fog_state[dest]["load"]) if dest != "cloud" else 0.3
                    lat, eng = step_latency(step_MI, data_in_KB, dest, fog_load), \
                               step_energy(step_MI, data_in_KB, dest)

                    step_dests[step_id] = dest
                    if classify_step(step_MI) == "boulder":
                        n_boulders += 1
                    else:
                        n_pebbles += 1

                total_latency += lat
                total_energy += eng
                step_latencies[step_id] = lat
                step_energies[step_id] = eng

                # Check deadline for this step
                if step_info.get("deadline_ms") and lat > step_info["deadline_ms"]:
                    deadline_met = False

            # Create task record
            record = TaskRecord(
                task_id=task_id,
                system=system_type,
                seed=seed,
                scenario=scenario,
                vehicle_id=vehicle.vehicle_id,
                sim_time_s=sim_time,
                total_latency_ms=total_latency,
                total_energy_j=total_energy,
                deadline_met=total_latency <= 200.0,
                step2_latency_ms=step_latencies.get(2, 0.0),
                step3_latency_ms=step_latencies.get(3, 0.0),
                step4_latency_ms=step_latencies.get(4, 0.0),
                step5_latency_ms=step_latencies.get(5, 0.0),
                step2_energy_j=step_energies.get(2, 0.0),
                step3_energy_j=step_energies.get(3, 0.0),
                step4_energy_j=step_energies.get(4, 0.0),
                step5_energy_j=step_energies.get(5, 0.0),
                step2_dest=step_dests.get(2, "unknown"),
                step3_dest=step_dests.get(3, "unknown"),
                step5_dest=step_dests.get(5, "unknown"),
                n_boulders=n_boulders,
                n_pebbles=n_pebbles,
                handoff_occurred=False,
                handoff_mode="none",
                handoff_success=False,
                t_exit_at_decision=0.0,
                fog_A_load=fog_state.get("A", {}).get("load", 0.0),
                fog_B_load=fog_state.get("B", {}).get("load", 0.0),
                fog_C_load=fog_state.get("C", {}).get("load", 0.0),
                fog_D_load=fog_state.get("D", {}).get("load", 0.0),
                fog_A_queue=fog_state.get("A", {}).get("queue", 0),
                fog_B_queue=fog_state.get("B", {}).get("queue", 0),
                fog_C_queue=fog_state.get("C", {}).get("queue", 0),
                fog_D_queue=fog_state.get("D", {}).get("queue", 0),
                agent_q_max=None,
                agent_epsilon=None,
                agent_reward=None,
                bc_loss_final=None,
                online_updates=0,
            )

            collector.add_record(record)
            task_counter += 1

        env.update_fog_loads(dt_s=1.0)

    return collector.records


def main():
    parser = argparse.ArgumentParser(description="Run PCNME simulations")
    parser.add_argument("--output", type=str, default="experiments/results/raw_results.csv",
                       help="Output CSV file for results")
    parser.add_argument("--weights", type=str, default="experiments/weights/",
                       help="Directory with pre-trained weights")
    parser.add_argument("--systems", nargs="+", default=SYSTEMS,
                       help="Systems to run")
    parser.add_argument("--scenarios", nargs="+", default=SCENARIOS,
                       help="Scenarios to run")
    parser.add_argument("--seeds", nargs="+", type=int, default=SEEDS,
                       help="Seeds to use")
    parser.add_argument("--n-vehicles", type=int, default=N_VEHICLES,
                       help="Number of vehicles per scenario")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    output_path = _resolve_repo_relative(args.output, repo_root)
    weights_dir = _resolve_repo_relative(args.weights, repo_root)

    all_records = []
    total_runs = len(args.systems) * len(args.scenarios) * len(args.seeds)
    run_count = 0

    for system in args.systems:
        for scenario in args.scenarios:
            for seed in args.seeds:
                run_count += 1
                print(f"[{run_count}/{total_runs}] Running {system} × {scenario} × seed={seed}")

                weights_path = (
                    _find_weights_file(weights_dir, repo_root)
                    if system in ["dqn_bc_only", "proposed"]
                    else None
                )

                records = run_simulation(system, scenario, seed,
                                       args.n_vehicles, weights_path)
                all_records.extend(records)

                print(f"      {len(records)} tasks completed")

    # Save results
    from pcnme import MetricsCollector
    collector = MetricsCollector(records=all_records)
    collector.save_csv(output_path)

    print(f"\n✓ Simulation complete. Results saved to {output_path}")
    print(f"  Total tasks: {len(all_records)}")


if __name__ == "__main__":
    main()
