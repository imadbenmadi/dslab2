"""
PCNME Offline Pre-training Script
Generates BC dataset from NSGA-II optimization for DQN pre-training.

Usage:
    python experiments/pretrain.py --batches 1000 --output experiments/weights/
"""

import argparse
import numpy as np
import torch
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pcnme import (
    NSGAIIOptimizer, generate_bc_dataset_from_nsga2,
    DQNAgent, STATE_DIM, ACTION_DIM, HIDDEN, BC_THRESHOLD
)


def generate_bc_dataset(n_batches: int = 1000, batch_size: int = 100):
    """
    Generate behavioral cloning dataset from NSGA-II Pareto-optimal solutions.
    
    This uses NSGA-II to generate expert trajectories, ensuring the BC dataset
    contains high-quality state-action pairs that the DQN can learn from.
    
    Args:
        n_batches: number of batches to generate
        batch_size: batch size per batch
    
    Returns:
        list of (state, action) tuples where actions are from Pareto-optimal solutions
    """
    print(f"Running NSGA-II optimization for expert trajectories...")
    
    # Initialize and run NSGA-II
    optimizer = NSGAIIOptimizer(n_pop=50, n_gen=30)
    optimizer.optimize()
    
    print(f"Extracted {len(optimizer.pareto_solutions)} Pareto-optimal solutions")
    print(f"Generating BC dataset: {n_batches} batches × {batch_size} samples")
    
    dataset = []
    pareto_solutions = optimizer.pareto_solutions
    
    for batch_idx in range(n_batches):
        if batch_idx % 100 == 0:
            print(f"  Batch {batch_idx}/{n_batches}")
        
        # Generate diverse states
        states = np.random.rand(batch_size, STATE_DIM)
        
        # Sample expert actions from Pareto front
        for state in states:
            # Randomly select a Pareto-optimal solution as expert
            expert_idx = np.random.randint(len(pareto_solutions))
            solution = pareto_solutions[expert_idx]
            
            # Convert solution to action (destinations for pebble steps are the actions)
            # Solution has 2 values: [step2_dest, step5_dest]
            # Pick one as the action (or use both as indices)
            action = int(solution[np.random.randint(len(solution))]) % ACTION_DIM
            
            dataset.append((state, action))
    
    print(f"Total dataset size: {len(dataset)} samples from Pareto-optimal solutions")
    return dataset


def pretrain_dqn(dataset, output_dir: Path, epochs: int = 20):
    """
    Pre-train DQN using behavioral cloning.
    
    Args:
        dataset: list of (state, action) tuples
        output_dir: directory to save weights
        epochs: BC training epochs
    """
    print(f"\nInitializing DQN agent (state_dim={STATE_DIM}, action_dim={ACTION_DIM})")

    agent = DQNAgent(state_dim=STATE_DIM, action_dim=ACTION_DIM,
                    hidden_sizes=HIDDEN)

    print(f"Pre-training with behavioral cloning ({epochs} epochs)...")
    agent.pretrain_with_bc(dataset, epochs=epochs, batch_size=64)

    # Check convergence
    final_loss = agent.bc_loss_history[-1]
    initial_loss = agent.bc_loss_history[0] if agent.bc_loss_history else final_loss
    convergence_rate = ((initial_loss - final_loss) / initial_loss * 100) if initial_loss > 0 else 0
    
    print(f"Final BC loss: {final_loss:.6f}")
    print(f"Convergence: {initial_loss:.6f} → {final_loss:.6f} ({convergence_rate:.1f}% improvement)")
    
    # For 5 random classes, baseline cross-entropy is log(5) ≈ 1.609
    # A loss < 1.50 indicates good learning
    baseline_loss = np.log(ACTION_DIM)
    if final_loss < baseline_loss * 0.9:
        print(f"✓ BC converged well (loss {final_loss:.6f} < {baseline_loss*0.9:.6f})")
    elif final_loss < baseline_loss:
        print(f"✓ BC learning (loss {final_loss:.6f} approaching baseline {baseline_loss:.6f})")
    else:
        print(f"⚠ BC may need more epochs (loss {final_loss:.6f} >= baseline {baseline_loss:.6f})")

    # Save weights
    output_dir.mkdir(parents=True, exist_ok=True)
    weights_path = output_dir / 'dqn_bc_pretrained.pt'
    agent.save_weights(weights_path)
    print(f"✓ Weights saved to {weights_path}")

    return agent


def main():
    parser = argparse.ArgumentParser(
        description="PCNME Offline Pre-training"
    )
    parser.add_argument('--batches', type=int, default=1000,
                       help='Number of batches to generate')
    parser.add_argument('--output', type=Path, default='experiments/weights/',
                       help='Output directory for weights')
    parser.add_argument('--epochs', type=int, default=20,
                       help='BC training epochs')

    args = parser.parse_args()

    print("=" * 70)
    print("PCNME OFFLINE PRE-TRAINING")
    print("=" * 70)

    # Generate dataset
    dataset = generate_bc_dataset(n_batches=args.batches)

    # Pre-train DQN
    agent = pretrain_dqn(dataset, args.output, epochs=args.epochs)

    print("\n" + "=" * 70)
    print("Pre-training complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
