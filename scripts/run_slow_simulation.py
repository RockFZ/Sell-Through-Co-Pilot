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
from src.forecast import forecast_bundle, OrbitConfig  # pylint: disable=wrong-import-position
from src.promo import build_lift_table, RobynConfig  # pylint: disable=wrong-import-position
from src.simulations import SimulationConfig, run_inventory_simulation  # pylint: disable=wrong-import-position

# Try to import ERP clients (optional)
try:
    from src.erp import OdooClient, ERPNextClient, OdooConfig, ERPNextConfig
    ERP_AVAILABLE = True
except ImportError:
    ERP_AVAILABLE = False
    OdooClient = None
    ERPNextClient = None
    OdooConfig = None
    ERPNextConfig = None


def run_pipeline(
    horizon_days: int,
    use_erp_sync: bool = False,
    orbit_config: OrbitConfig | None = None,
    robyn_config: RobynConfig | None = None,
) -> tuple[pd.DataFrame, dict]:
    raw_frames = data_loader.load_raw_frames()
    snapshot = transformations.build_planning_snapshot(raw_frames)
    sim_inputs = sim_prep.prepare_simulation_inputs(raw_frames)

    # Sync ERP inventory if requested
    product_features = snapshot["product_features"].copy()
    if use_erp_sync and ERP_AVAILABLE:
        print("Syncing inventory from ERP systems...")
        # Sync Odoo products (SKU-001, SKU-003)
        odoo_config = OdooConfig(use_mock=True)  # Use mock for MVP
        odoo_client = OdooClient(odoo_config)
        odoo_products = product_features[product_features["sku"].isin(["SKU-001", "SKU-003"])]
        if not odoo_products.empty:
            product_features = pd.concat([
                odoo_client.sync_inventory_to_dataframe(odoo_products),
                product_features[~product_features["sku"].isin(["SKU-001", "SKU-003"])],
            ]).reset_index(drop=True)
        
        # Sync ERPNext products (SKU-002, SKU-004)
        erpnext_config = ERPNextConfig(use_mock=True)  # Use mock for MVP
        erpnext_client = ERPNextClient(erpnext_config)
        erpnext_products = product_features[product_features["sku"].isin(["SKU-002", "SKU-004"])]
        if not erpnext_products.empty:
            product_features = pd.concat([
                erpnext_client.sync_inventory_to_dataframe(erpnext_products),
                product_features[~product_features["sku"].isin(["SKU-002", "SKU-004"])],
            ]).reset_index(drop=True)
        
        print("ERP sync complete.")

    # Generate forecasts using Orbit (or enhanced stub)
    orbit_cfg = orbit_config or OrbitConfig()
    forecasts = forecast_bundle(snapshot["daily_demand"], config=orbit_cfg)
    
    horizon_dates = pd.date_range(
        snapshot["daily_demand"]["date"].max() + pd.Timedelta(days=1),
        periods=horizon_days,
        freq="D",
    )

    # Generate lift table using Robyn (or enhanced stub)
    robyn_cfg = robyn_config or RobynConfig()
    lifts = build_lift_table(
        sim_inputs["expanded_promos"],
        snapshot["ad_spend"],
        snapshot["product_features"]["product_id"],
        horizon_dates,
        config=robyn_cfg,
        historical_sales=snapshot["daily_demand"],  # Pass historical data for Robyn
    )

    schedule = sim_inputs["simulation_schedule"].copy()
    schedule = schedule[schedule["date"].isin(horizon_dates)]
    
    # Update schedule with synced product features
    schedule = schedule.merge(
        product_features[["product_id", "on_hand_units", "on_order_units", "reserved_units"]],
        on="product_id",
        how="left",
        suffixes=("", "_synced"),
    )
    # Use synced values if available
    schedule["on_hand_units"] = schedule["on_hand_units_synced"].fillna(schedule["on_hand_units"])
    schedule["on_order_units"] = schedule["on_order_units_synced"].fillna(schedule["on_order_units"])
    schedule["reserved_units"] = schedule["reserved_units_synced"].fillna(schedule["reserved_units"])
    schedule = schedule.drop(columns=["on_hand_units_synced", "on_order_units_synced", "reserved_units_synced"], errors="ignore")

    simulation_log = run_inventory_simulation(
        schedule,
        product_features,  # Use synced product features
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
    parser.add_argument(
        "--use-erp-sync",
        action="store_true",
        help="Sync inventory from ERP systems (Odoo/ERPNext).",
    )
    args = parser.parse_args()

    log_df, summary = run_pipeline(
        args.horizon_days,
        use_erp_sync=args.use_erp_sync,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.output_dir / "sim_log.parquet"
    log_df.to_parquet(log_path, index=False)

    summary_path = args.output_dir / "sim_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    print("Slow simulation complete.")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

