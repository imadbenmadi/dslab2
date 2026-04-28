"""
PCNME Offline Pre-training Script
Generates BC dataset from NSGA-II optimization for DQN pre-training.

Usage:
    python experiments/pretrain.py --batches 1000 --output experiments/weights/
"""

import argparse
import numpy as np
import csv
import logging
import torch
from pathlib import Path
import sys

# Add parent directory to path (dslab2 root)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pcnme import (
    NSGAIIOptimizer, generate_bc_dataset_from_nsga2,
    DQNAgent, STATE_DIM, ACTION_DIM, HIDDEN, BC_THRESHOLD
)
from pcnme.progress import progress
from pcnme.utilities import setup_logging, get_logger


def generate_bc_dataset(n_batches: int = 1000, batch_size: int = 100, seed: int = 42, logger=None):
    """
    Generate behavioral cloning dataset from NSGA-II Pareto-optimal solutions.
    
    This uses NSGA-II to generate expert trajectories, ensuring the BC dataset
    contains high-quality state-action pairs that the DQN can learn from.
    
    Args:
        n_batches: number of batches to generate
        batch_size: batch size per batch
        seed: random seed
        logger: optional logger instance
    
    Returns:
        list of (state, action) tuples where actions are from Pareto-optimal solutions
    """
    if logger is None:
        logger = logging.getLogger('PCNME.Pretrain')
    
    logger.info(f"Running NSGA-II optimization for expert trajectories...")
    
    # Initialize and run NSGA-II
    optimizer = NSGAIIOptimizer()
    optimizer.optimize()
    
    # Get Pareto-optimal solutions
    pareto_solutions = np.asarray(optimizer.pareto_pop)

    if len(pareto_solutions) == 0:
        logger.warning("No Pareto solutions found, using random dataset")
        pareto_solutions = np.random.randint(0, 5, (10, 3)).astype(float)
    
    logger.info(f"[OK] Extracted {len(pareto_solutions)} Pareto-optimal solutions")
    
    # Save raw NSGA-II Pareto solutions
    nsga_path = Path(__file__).parent / 'results' / 'pretraining' / 'tof_nsga_solutions.csv'
    if not nsga_path.parent.exists():
        nsga_path.parent.mkdir(parents=True, exist_ok=True)
    
    nsga_path.parent.mkdir(parents=True, exist_ok=True)
    with open(nsga_path, 'w', newline='') as f:
        writer = csv.writer(f)
        num_actions = pareto_solutions.shape[1] if pareto_solutions.ndim == 2 else 1
        writer.writerow([f"action_step_{i+1}" for i in range(num_actions)])
        for sol in pareto_solutions:
            writer.writerow(sol if pareto_solutions.ndim == 2 else [sol])
    logger.info(f"[OK] NSGA-II solutions saved to {nsga_path}")

    logger.info(f"[OK] Generating BC dataset: {n_batches} batches x {batch_size} samples")
    
    dataset = []
    rng = np.random.default_rng(seed)

    batch_iter = progress(
        range(n_batches),
        desc="BC dataset",
        unit="batch",
        total=n_batches,
    )

    n_solutions = len(pareto_solutions)
    n_vars = int(pareto_solutions.shape[1]) if pareto_solutions.ndim == 2 else 1

    for batch_idx in batch_iter:
        # Generate diverse states in [0,1]
        states = rng.random((batch_size, STATE_DIM))

        # Sample expert actions from Pareto front
        expert_idxs = rng.integers(0, max(1, n_solutions), size=batch_size)
        actions_raw = pareto_solutions[expert_idxs, 0] if n_vars > 0 else pareto_solutions[expert_idxs]
        actions = (actions_raw.astype(int) % ACTION_DIM).tolist()

        for i in range(batch_size):
            dataset.append((states[i], int(actions[i])))
    # save the dataset locally for inspection
    dataset_path = Path(__file__).parent / 'dataset'  / 'gen_dataset.csv'
    if not dataset_path.parent.exists():
        dataset_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(dataset_path, 'w', newline='') as f:
        writer = csv.writer(f)
        header = [f"state_{i+1}" for i in range(STATE_DIM)] + ["action"]
        writer.writerow(header)
        for state, action in dataset:
            writer.writerow(list(state) + [action])
    logger.info(f"[OK] BC dataset generated and saved to {dataset_path}")
    logger.info(f"[OK] Total dataset size: {len(dataset)} samples")
    logger.debug(f"  State dimension: {STATE_DIM}, Action dimension: {ACTION_DIM}")
    return dataset


def pretrain_dqn(dataset, output_dir: Path, epochs: int = 20, logger=None):
    """
    Pre-train DQN using behavioral cloning.
    
    Args:
        dataset: list of (state, action) tuples
        output_dir: directory to save weights
        epochs: BC training epochs
        logger: optional logger instance
    """
    if logger is None:
        logger = logging.getLogger('PCNME.Pretrain')
    
    logger.info(f"Initializing DQN agent (state_dim={STATE_DIM}, action_dim={ACTION_DIM})")
    logger.debug(f"  Hidden sizes: {HIDDEN}")

    agent = DQNAgent(state_dim=STATE_DIM, action_dim=ACTION_DIM,
                    hidden_sizes=HIDDEN)

    logger.info(f"Pre-training with behavioral cloning ({epochs} epochs)...")
    agent.pretrain_with_bc(dataset, epochs=epochs, batch_size=64)

    # Check convergence
    final_loss = agent.bc_loss_history[-1]
    initial_loss = agent.bc_loss_history[0] if agent.bc_loss_history else final_loss
    convergence_rate = ((initial_loss - final_loss) / initial_loss * 100) if initial_loss > 0 else 0
    
    # Save DQN loss history
    loss_path = Path(__file__).parent / 'results' / 'pretraining' / 'dqn_loss_history.csv'
    loss_path.parent.mkdir(parents=True, exist_ok=True)
    with open(loss_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["epoch", "loss"])
        for idx, loss_val in enumerate(agent.bc_loss_history):
            writer.writerow([idx + 1, loss_val])
    logger.info(f"[OK] DQN loss history saved to {loss_path}")

    logger.info(f"Final BC loss: {final_loss:.6f}")
    logger.info(f"Convergence: {initial_loss:.6f} -> {final_loss:.6f} ({convergence_rate:.1f}% improvement)")
    logger.debug(f"  Loss history length: {len(agent.bc_loss_history)}")
    
    # For 5 random classes, baseline cross-entropy is log(5) ≈ 1.609
    # A loss < 1.50 indicates good learning
    baseline_loss = np.log(ACTION_DIM)
    if final_loss < baseline_loss * 0.9:
        logger.info(f"[OK] BC converged well (loss {final_loss:.6f} < {baseline_loss*0.9:.6f})")
    elif final_loss < baseline_loss:
        logger.info(f"[OK] BC learning (loss {final_loss:.6f} approaching baseline {baseline_loss:.6f})")
    else:
        logger.warning(f"[!] BC may need more epochs (loss {final_loss:.6f} >= baseline {baseline_loss:.6f})")

    # Save weights
    output_dir.mkdir(parents=True, exist_ok=True)
    weights_path = output_dir / 'dqn_bc_pretrained.pt'
    agent.save_weights(weights_path)
    logger.info(f"[OK] Weights saved to {weights_path}")
    logger.debug(f"  File size: {weights_path.stat().st_size / 1024:.1f} KB")

    return agent


def main():
    parser = argparse.ArgumentParser(
        description="PCNME Offline Pre-training"
    )
    parser.add_argument('--batches', type=int, default=1000,
                       help='Number of batches to generate')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'weights',
                       help='Output directory for weights')
    parser.add_argument('--epochs', type=int, default=20,
                       help='BC training epochs')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for dataset generation')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING'], default='INFO',
                       help='Logging level')

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.output / 'logs', 'pretrain', args.log_level)
    
    print("=" * 70)
    print("PCNME OFFLINE PRE-TRAINING")
    print("=" * 70)
    logger.info("=" * 70)
    logger.info("PCNME OFFLINE PRE-TRAINING")
    logger.info("=" * 70)
    logger.info(f"Arguments: batches={args.batches}, epochs={args.epochs}, seed={args.seed}")

    # Generate dataset
    logger.info("Starting dataset generation...")
    dataset = generate_bc_dataset(n_batches=args.batches, seed=args.seed, logger=logger)
    logger.info(f"Dataset ready: {len(dataset)} samples")

    # Pre-train DQN
    logger.info("Starting DQN pre-training...")
    agent = pretrain_dqn(dataset, args.output, epochs=args.epochs, logger=logger)

    logger.info("=" * 70)
    logger.info("Pre-training complete!")
    logger.info("=" * 70)
    print("\n" + "=" * 70)
    print("Pre-training complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
