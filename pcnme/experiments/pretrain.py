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

# Import dataset generation logic from utilities
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utilities.data_gen import generate_bc_dataset


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
    parser.add_argument('--batches', type=int, default=20,
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
    
    print("\n" + "🚀 " * 20)
    print("    PCNME OFFLINE PRE-TRAINING (REAL NSGA-II MATH)")
    print("🚀 " * 20 + "\n")
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
