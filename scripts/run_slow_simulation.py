#!/usr/bin/env python3
"""
Run slow inventory simulations using Orbit and Robyn python facsimiles.
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

from src import data_loader, sim_prep, transformations  # pylint: disable=wrong-import-position
from src.forecast import forecast_bundle  # pylint: disable=wrong-import-position
from src.promo import build_lift_table  # pylint: disable=wrong-import-position
from src.simulations import SimulationConfig, run_inventory_simulation  # pylint: disable=wrong-import-position


def run_pipeline(horizon_days: int) -> tuple[pd.DataFrame, dict]:
    raw_frames = data_loader.load_raw_frames()
    snapshot = transformations.build_planning_snapshot(raw_frames)
    sim_inputs = sim_prep.prepare_simulation_inputs(raw_frames)

    forecasts = forecast_bundle(snapshot["daily_demand"])
    horizon_dates = pd.date_range(
        snapshot["daily_demand"]["date"].max() + pd.Timedelta(days=1),
        periods=horizon_days,
        freq="D",
    )

    lifts = build_lift_table(
        sim_inputs["expanded_promos"],
        snapshot["ad_spend"],
        snapshot["product_features"]["product_id"],
        horizon_dates,
    )

    schedule = sim_inputs["simulation_schedule"].copy()
    schedule = schedule[schedule["date"].isin(horizon_dates)]

    simulation_log = run_inventory_simulation(
        schedule,
        snapshot["product_features"],
        lifts,
        forecasts,
        SimulationConfig(),
    )

    summary = (
        simulation_log.groupby("product_id")
        .agg(
            total_projected_demand=("projected_demand", "sum"),
            total_realized_demand=("realized_demand", "sum"),
            total_lost_sales=("lost_sales", "sum"),
            total_orders=("order_qty", "sum"),
        )
        .reset_index()
    )

    return simulation_log, {
        "records": len(simulation_log),
        "products": summary.to_dict(orient="records"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=30,
        help="Number of days to simulate ahead.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/slow_simulations"),
        help="Directory to store simulation logs.",
    )
    args = parser.parse_args()

    log_df, summary = run_pipeline(args.horizon_days)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.output_dir / "sim_log.parquet"
    log_df.to_parquet(log_path, index=False)

    summary_path = args.output_dir / "sim_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    print("Slow simulation complete.")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

