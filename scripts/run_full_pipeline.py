#!/usr/bin/env python3
"""
Run the complete Sell-Through Co-Pilot pipeline end-to-end.
Logs all outputs to a file.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


class PipelineLogger:
    """Logger that writes to both console and file."""
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.file_handle = open(log_file, "w", encoding="utf-8")
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message to both console and file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        self.file_handle.write(log_entry + "\n")
        self.file_handle.flush()
    
    def log_section(self, title: str):
        """Log a section header."""
        separator = "=" * 80
        self.log("")
        self.log(separator)
        self.log(f"  {title}")
        self.log(separator)
    
    def log_json(self, data: dict, title: str = "Data"):
        """Log JSON data in a readable format."""
        self.log(f"\n{title}:")
        self.log(json.dumps(data, indent=2))
    
    def close(self):
        """Close the log file."""
        self.file_handle.close()


def run_data_pipeline(logger: PipelineLogger) -> dict:
    """Run the data pipeline."""
    logger.log_section("STEP 1: Data Pipeline")
    
    try:
        from src import data_loader, transformations, sim_prep
        import pandas as pd
        
        logger.log("Loading raw data...")
        start_time = time.time()
        
        raw_frames = data_loader.load_raw_frames()
        logger.log(f"  Loaded {len(raw_frames)} raw datasets")
        
        logger.log("Building planning snapshot...")
        snapshot = transformations.build_planning_snapshot(raw_frames)
        logger.log(f"  Daily demand: {len(snapshot['daily_demand'])} records")
        logger.log(f"  Product features: {len(snapshot['product_features'])} products")
        
        logger.log("Preparing simulation inputs...")
        sim_inputs = sim_prep.prepare_simulation_inputs(raw_frames)
        logger.log(f"  Expanded promos: {len(sim_inputs['expanded_promos'])} records")
        logger.log(f"  Simulation schedule: {len(sim_inputs['simulation_schedule'])} records")
        
        elapsed = time.time() - start_time
        logger.log(f"✓ Data pipeline completed in {elapsed:.2f} seconds")
        
        # Create summary
        summary = {
            "daily_demand": {
                "rows": len(snapshot["daily_demand"]),
                "columns": list(snapshot["daily_demand"].columns),
            },
            "product_features": {
                "rows": len(snapshot["product_features"]),
                "columns": list(snapshot["product_features"].columns),
            },
            "expanded_promos": {
                "rows": len(sim_inputs["expanded_promos"]),
                "columns": list(sim_inputs["expanded_promos"].columns),
            },
            "simulation_schedule": {
                "rows": len(sim_inputs["simulation_schedule"]),
                "columns": list(sim_inputs["simulation_schedule"].columns),
            },
        }
        
        logger.log_json(summary, "Pipeline Summary")
        return summary
    except Exception as e:
        logger.log(f"✗ Data pipeline failed: {e}", "ERROR")
        import traceback
        logger.log(traceback.format_exc(), "ERROR")
        raise


def run_slow_simulation(logger: PipelineLogger, horizon_days: int = 21) -> tuple:
    """Run the slow simulation."""
    logger.log_section("STEP 2: Slow Simulation")
    
    try:
        from scripts.run_slow_simulation import run_pipeline
        
        logger.log(f"Running simulation for {horizon_days} days...")
        start_time = time.time()
        
        simulation_log, summary = run_pipeline(horizon_days=horizon_days)
        
        elapsed = time.time() - start_time
        
        logger.log(f"✓ Simulation completed in {elapsed:.2f} seconds")
        logger.log(f"  Records: {len(simulation_log)}")
        logger.log(f"  Products: {simulation_log['product_id'].nunique()}")
        logger.log_json(summary, "Simulation Summary")
        
        # Log sample of simulation log
        logger.log("\nSample Simulation Log (first 5 rows):")
        logger.log(simulation_log.head().to_string())
        
        return simulation_log, summary
    except Exception as e:
        logger.log(f"✗ Simulation failed: {e}", "ERROR")
        raise


def train_surrogate_model(logger: PipelineLogger, use_gpu: bool = True, simulation_logs: pd.DataFrame = None) -> tuple:
    """Train the surrogate model."""
    logger.log_section("STEP 3: Surrogate Model Training")
    
    try:
        from src.surrogate import train_surrogate_model, SurrogateConfig
        from src import data_loader, transformations
        from src.sim_prep import prepare_simulation_inputs
        import pandas as pd
        
        # Load data
        logger.log("Loading simulation logs and features...")
        
        if simulation_logs is None:
            sim_log_path = PROJECT_ROOT / "data/processed/slow_simulations/sim_log.parquet"
            if sim_log_path.exists():
                try:
                    simulation_logs = pd.read_parquet(sim_log_path)
                except Exception as e:
                    logger.log(f"  Warning: Could not read parquet file: {e}")
                    logger.log("  Will use simulation from previous step if available")
                    raise FileNotFoundError("Need simulation logs from previous step")
            else:
                raise FileNotFoundError(f"Simulation logs not found: {sim_log_path}")
        
        logger.log(f"  Loaded {len(simulation_logs)} simulation records")
        
        raw_frames = data_loader.load_raw_frames()
        snapshot = transformations.build_planning_snapshot(raw_frames)
        sim_inputs = prepare_simulation_inputs(raw_frames)
        
        logger.log(f"  Products: {simulation_logs['product_id'].nunique()}")
        logger.log(f"  Training with GPU: {use_gpu}")
        
        # Configure and train
        config = SurrogateConfig(use_gpu=use_gpu, test_size=0.2)
        
        start_time = time.time()
        model, training_metrics = train_surrogate_model(
            simulation_logs,
            snapshot["product_features"],
            sim_inputs["expanded_promos"],
            snapshot["ad_spend"],
            config=config,
        )
        elapsed = time.time() - start_time
        
        logger.log(f"✓ Model training completed in {elapsed:.2f} seconds")
        logger.log_json(training_metrics, "Training Metrics")
        
        # Save model
        model_dir = PROJECT_ROOT / "data/processed/surrogate_model"
        model.save(model_dir)
        logger.log(f"✓ Model saved to {model_dir}")
        
        return model, training_metrics
    except Exception as e:
        logger.log(f"✗ Model training failed: {e}", "ERROR")
        import traceback
        logger.log(traceback.format_exc(), "ERROR")
        raise


def create_dashboard(logger: PipelineLogger, use_slow_simulation: bool = False) -> dict:
    """Create the dashboard."""
    logger.log_section("STEP 4: Dashboard Creation")
    
    try:
        from src.surrogate import SurrogateModel, prepare_prediction_features
        from src.dashboard import create_dashboard
        from src import data_loader, transformations
        from src.sim_prep import prepare_simulation_inputs
        import pandas as pd
        
        # Load model
        model_dir = PROJECT_ROOT / "data/processed/surrogate_model"
        if not model_dir.exists():
            raise FileNotFoundError(f"Model not found: {model_dir}")
        
        logger.log("Loading trained model...")
        model = SurrogateModel.load(model_dir)
        logger.log(f"  Model targets: {model.target_names}")
        
        # Load data
        logger.log("Loading product features and planning data...")
        raw_frames = data_loader.load_raw_frames()
        snapshot = transformations.build_planning_snapshot(raw_frames)
        sim_inputs = prepare_simulation_inputs(raw_frames)
        
        # Prepare features and predict
        logger.log("Preparing features and generating predictions...")
        features = prepare_prediction_features(
            snapshot["product_features"],
            sim_inputs["expanded_promos"],
            snapshot["ad_spend"],
        )
        
        predictions = model.predict(features)
        logger.log(f"✓ Generated predictions for {len(predictions)} products")
        
        # Load or generate simulation logs for timeline
        simulation_logs = None
        if use_slow_simulation:
            logger.log("Running slow simulation for risk timeline...")
            from scripts.run_slow_simulation import run_pipeline
            simulation_logs, _ = run_pipeline(horizon_days=21)
        else:
            sim_log_path = PROJECT_ROOT / "data/processed/slow_simulations/sim_log.parquet"
            if sim_log_path.exists():
                logger.log("Loading simulation logs for risk timeline...")
                simulation_logs = pd.read_parquet(sim_log_path)
        
        # Create dashboard
        logger.log("Creating dashboard...")
        dashboard = create_dashboard(
            predictions,
            snapshot["product_features"],
            simulation_logs=simulation_logs,
        )
        
        dashboard_data = dashboard.generate_dashboard_data(
            predictions,
            snapshot["product_features"],
            simulation_logs=simulation_logs,
        )
        
        # Save dashboard
        dashboard_path = PROJECT_ROOT / "data/processed/dashboard.json"
        dashboard.save_dashboard(dashboard_data, dashboard_path)
        logger.log(f"✓ Dashboard saved to {dashboard_path}")
        
        # Log dashboard summary
        logger.log("\nDashboard Summary:")
        logger.log(f"  Overall Status: {dashboard_data['readiness']['overall_status'].upper()}")
        logger.log(f"  Products:")
        for product in dashboard_data["readiness"]["products"]:
            status_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(product["status"], "⚪")
            logger.log(f"    {status_emoji} {product['name']} ({product['product_id']}): {product['status']}")
            logger.log(f"      Service Level: {product['service_level']:.1%}")
            logger.log(f"      Lost Sales Rate: {product['lost_sales_rate']:.1%}")
        
        if dashboard_data["risk_timeline"]:
            risk_df = pd.DataFrame(dashboard_data["risk_timeline"])
            if "risk_level" in risk_df.columns:
                risk_summary = risk_df["risk_level"].value_counts().to_dict()
                logger.log(f"\n  Risk Timeline Summary:")
                for level, count in risk_summary.items():
                    logger.log(f"    {level}: {count} records")
        
        return dashboard_data
    except Exception as e:
        logger.log(f"✗ Dashboard creation failed: {e}", "ERROR")
        import traceback
        logger.log(traceback.format_exc(), "ERROR")
        raise


def main():
    parser = argparse.ArgumentParser(description="Run complete Sell-Through Co-Pilot pipeline")
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("data/processed/pipeline_run.log"),
        help="Path to log file.",
    )
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=21,
        help="Simulation horizon in days.",
    )
    parser.add_argument(
        "--use-gpu",
        action="store_true",
        default=True,
        help="Use GPU for surrogate model training.",
    )
    parser.add_argument(
        "--no-gpu",
        action="store_false",
        dest="use_gpu",
        help="Disable GPU for training.",
    )
    parser.add_argument(
        "--skip-data-pipeline",
        action="store_true",
        help="Skip data pipeline step (assume data already processed).",
    )
    parser.add_argument(
        "--skip-simulation",
        action="store_true",
        help="Skip simulation step (assume simulation already run).",
    )
    parser.add_argument(
        "--skip-training",
        action="store_true",
        help="Skip surrogate model training (assume model already trained).",
    )
    parser.add_argument(
        "--skip-dashboard",
        action="store_true",
        help="Skip dashboard creation.",
    )
    args = parser.parse_args()
    
    # Initialize logger
    logger = PipelineLogger(args.log_file)
    
    try:
        logger.log_section("SELL-THROUGH CO-PILOT - FULL PIPELINE RUN")
        logger.log(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.log(f"Log file: {args.log_file}")
        logger.log(f"Horizon days: {args.horizon_days}")
        logger.log(f"Use GPU: {args.use_gpu}")
        
        overall_start = time.time()
        
        # Step 1: Data Pipeline
        if not args.skip_data_pipeline:
            pipeline_summary = run_data_pipeline(logger)
        else:
            logger.log_section("STEP 1: Data Pipeline (SKIPPED)")
            logger.log("Skipping data pipeline step")
        
        # Step 2: Slow Simulation
        if not args.skip_simulation:
            simulation_log, sim_summary = run_slow_simulation(logger, args.horizon_days)
        else:
            logger.log_section("STEP 2: Slow Simulation (SKIPPED)")
            logger.log("Skipping simulation step")
        
        # Step 3: Train Surrogate Model
        if not args.skip_training:
            # Pass simulation_logs from previous step if available
            sim_logs = simulation_log if not args.skip_simulation else None
            model, training_metrics = train_surrogate_model(logger, args.use_gpu, simulation_logs=sim_logs)
        else:
            logger.log_section("STEP 3: Surrogate Model Training (SKIPPED)")
            logger.log("Skipping model training step")
        
        # Step 4: Create Dashboard
        if not args.skip_dashboard:
            dashboard_data = create_dashboard(logger, use_slow_simulation=False)
        else:
            logger.log_section("STEP 4: Dashboard Creation (SKIPPED)")
            logger.log("Skipping dashboard creation step")
        
        # Final summary
        overall_elapsed = time.time() - overall_start
        logger.log_section("PIPELINE COMPLETE")
        logger.log(f"Total execution time: {overall_elapsed:.2f} seconds")
        logger.log(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.log("✓ All steps completed successfully!")
        
    except Exception as e:
        logger.log_section("PIPELINE FAILED")
        logger.log(f"Error: {e}", "ERROR")
        import traceback
        logger.log(traceback.format_exc(), "ERROR")
        sys.exit(1)
    finally:
        logger.close()


if __name__ == "__main__":
    main()

