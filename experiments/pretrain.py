"""
Pre-training script: generate BC dataset and pre-train DQN agent.
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pcnme import (
    DQNAgent, generate_bc_dataset_from_nsga2,
    N_OFFLINE_BATCHES
)


def main():
    parser = argparse.ArgumentParser(
        description="Pre-train DQN agent with behavioral cloning"
    )
    parser.add_argument("--batches", type=int, default=N_OFFLINE_BATCHES,
                       help="Number of BC dataset samples")
    parser.add_argument("--epochs", type=int, default=20,
                       help="Number of BC training epochs")
    parser.add_argument("--output", type=str, default="experiments/weights/",
                       help="Output directory for weights")
    parser.add_argument("--batch-size", type=int, default=32,
                       help="Batch size for pre-training")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("[1/3] Generating BC dataset from NSGA-II...")
    bc_dataset = generate_bc_dataset_from_nsga2(n_samples=args.batches)
    print(f"      Generated {len(bc_dataset)} BC samples")

    print("[2/3] Initializing DQN agent...")
    agent = DQNAgent()
    print("      DQN network initialized")

    print("[3/3] Pre-training with behavioral cloning...")
    bc_loss = agent.pretrain_with_bc(bc_dataset, epochs=args.epochs,
                                     batch_size=args.batch_size)
    print(f"      Final BC loss: {bc_loss:.6f}")

    weights_path = output_dir / "dqn_bc_pretrained.pt"
    agent.save_weights(weights_path)
    print(f"\n✓ Pre-training complete. Weights saved to {weights_path}")


if __name__ == "__main__":
    main()
