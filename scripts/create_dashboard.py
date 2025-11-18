#!/usr/bin/env python3
"""
Create dashboard with readiness light and risk timeline.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src import data_loader, transformations  # pylint: disable=wrong-import-position
from src.sim_prep import prepare_simulation_inputs  # pylint: disable=wrong-import-position
from src.surrogate import SurrogateModel, prepare_prediction_features  # pylint: disable=wrong-import-position
from src.dashboard import create_dashboard, RiskThresholds  # pylint: disable=wrong-import-position


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("data/processed/surrogate_model"),
        help="Directory containing trained surrogate model.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/dashboard.json"),
        help="Output path for dashboard JSON.",
    )
    parser.add_argument(
        "--simulation-logs",
        type=Path,
        default=None,
        help="Optional simulation logs for risk timeline.",
    )
    parser.add_argument(
        "--use-slow-simulation",
        action="store_true",
        help="Run slow simulation to generate risk timeline.",
    )
    args = parser.parse_args()
    
    print("Loading model and data...")
    
    # Load model
    if not args.model_dir.exists():
        print(f"Error: Model directory not found: {args.model_dir}")
        print("Please train a model first using: python scripts/train_surrogate.py")
        sys.exit(1)
    
    model = SurrogateModel.load(args.model_dir)
    print(f"Loaded model with targets: {model.target_names}")
    
    # Load data
    raw_frames = data_loader.load_raw_frames()
    snapshot = transformations.build_planning_snapshot(raw_frames)
    sim_inputs = prepare_simulation_inputs(raw_frames)
    
    # Prepare prediction features
    print("Preparing features for prediction...")
    features = prepare_prediction_features(
        snapshot["product_features"],
        sim_inputs["expanded_promos"],
        snapshot["ad_spend"],
    )
    
    # Predict
    print("Generating predictions...")
    predictions = model.predict(features)
    
    # Load or generate simulation logs for timeline
    simulation_logs = None
    if args.simulation_logs and args.simulation_logs.exists():
        print(f"Loading simulation logs from {args.simulation_logs}")
        simulation_logs = pd.read_parquet(args.simulation_logs)
    elif args.use_slow_simulation:
        print("Running slow simulation for risk timeline...")
        from scripts.run_slow_simulation import run_pipeline
        simulation_logs, _ = run_pipeline(horizon_days=21)
    
    # Create dashboard
    print("Creating dashboard...")
    dashboard = create_dashboard(
        predictions,
        snapshot["product_features"],
        simulation_logs=simulation_logs,
    )
    
    # Generate dashboard data
    dashboard_data = dashboard.generate_dashboard_data(
        predictions,
        snapshot["product_features"],
        simulation_logs=simulation_logs,
    )
    
    # Save dashboard
    dashboard.save_dashboard(dashboard_data, args.output)
    
    print(f"\nDashboard saved to {args.output}")
    print("\nReadiness Status:")
    print(f"  Overall: {dashboard_data['readiness']['overall_status'].upper()}")
    for product in dashboard_data["readiness"]["products"]:
        status_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(product["status"], "⚪")
        print(f"  {status_emoji} {product['name']} ({product['product_id']}): {product['status']}")
        print(f"    Service Level: {product['service_level']:.1%}")
        print(f"    Lost Sales Rate: {product['lost_sales_rate']:.1%}")
    
    if dashboard_data["risk_timeline"]:
        print(f"\nRisk Timeline: {len(dashboard_data['risk_timeline'])} records")
        # Show summary by risk level
        risk_df = pd.DataFrame(dashboard_data["risk_timeline"])
        if "risk_level" in risk_df.columns:
            risk_summary = risk_df["risk_level"].value_counts()
            print("  Risk Level Distribution:")
            for level, count in risk_summary.items():
                print(f"    {level}: {count}")


if __name__ == "__main__":
    main()

