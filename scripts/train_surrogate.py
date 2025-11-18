#!/usr/bin/env python3
"""
Train surrogate model on simulation logs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src import data_loader, transformations  # pylint: disable=wrong-import-position
from src.sim_prep import prepare_simulation_inputs  # pylint: disable=wrong-import-position
from src.surrogate import train_surrogate_model, SurrogateConfig  # pylint: disable=wrong-import-position
from src.surrogate.validation import validate_on_holdout  # pylint: disable=wrong-import-position


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--simulation-logs",
        type=Path,
        default=Path("data/processed/slow_simulations/sim_log.parquet"),
        help="Path to simulation logs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/surrogate_model"),
        help="Directory to save trained model.",
    )
    parser.add_argument(
        "--use-gpu",
        action="store_true",
        default=True,
        help="Use GPU for training (default: True).",
    )
    parser.add_argument(
        "--no-gpu",
        action="store_false",
        dest="use_gpu",
        help="Disable GPU training.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of data to use for testing.",
    )
    args = parser.parse_args()
    
    print("Loading data...")
    # Load simulation logs
    simulation_logs = pd.read_parquet(args.simulation_logs)
    
    # Load raw data for features
    raw_frames = data_loader.load_raw_frames()
    snapshot = transformations.build_planning_snapshot(raw_frames)
    sim_inputs = prepare_simulation_inputs(raw_frames)
    
    print(f"Training on {len(simulation_logs)} simulation records")
    print(f"Products: {simulation_logs['product_id'].nunique()}")
    
    # Configure model
    config = SurrogateConfig(
        use_gpu=args.use_gpu,
        test_size=args.test_size,
    )
    
    print(f"\nTraining surrogate model (GPU: {args.use_gpu})...")
    model, training_metrics = train_surrogate_model(
        simulation_logs,
        snapshot["product_features"],
        sim_inputs["expanded_promos"],
        snapshot["ad_spend"],
        config=config,
    )
    
    print("\nTraining Metrics:")
    for target, metrics in training_metrics.items():
        print(f"  {target}:")
        print(f"    MAE: {metrics['mae']:.4f}")
        print(f"    RMSE: {metrics['rmse']:.4f}")
        print(f"    R²: {metrics['r2']:.4f}")
        print(f"    Train: {metrics['n_train']} samples, Test: {metrics['n_test']} samples")
    
    # Save model
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model.save(args.output_dir)
    
    print(f"\nModel saved to {args.output_dir}")
    
    # Save training metrics
    metrics_path = args.output_dir / "training_metrics.json"
    metrics_path.write_text(json.dumps(training_metrics, indent=2))
    
    print("Training complete!")


if __name__ == "__main__":
    main()

