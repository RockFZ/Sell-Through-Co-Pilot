"""
Simulation preparation utilities for Sell-Through Co-Pilot.
"""

from __future__ import annotations

from typing import Dict, Iterable

import pandas as pd


def expand_promos(promo_df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand promo rows so downstream simulations can join day-level lift factors.
    """

    promo_df = promo_df.copy()
    promo_df["start_date"] = pd.to_datetime(promo_df["start_date"])
    promo_df["end_date"] = pd.to_datetime(promo_df["end_date"])

    expanded_rows = []
    for _, row in promo_df.iterrows():
        for day in pd.date_range(row["start_date"], row["end_date"]):
            expanded_rows.append(
                {
                    "date": day,
                    "product_id": row["product_id"],
                    "promo_id": row["promo_id"],
                    "discount_pct": row["discount_pct"],
                    "description": row["description"],
                }
            )
    return pd.DataFrame(expanded_rows)


def build_simulation_schedule(
    product_features: pd.DataFrame,
    daily_demand: pd.DataFrame,
    expanded_promos: pd.DataFrame,
    horizon_days: int = 30,
) -> pd.DataFrame:
    """
    Construct the base table used by the slow simulation engine.
    """

    latest_date = daily_demand["date"].max()
    horizon = pd.date_range(latest_date + pd.Timedelta(days=1), periods=horizon_days, freq="D")
    future_frame = pd.MultiIndex.from_product(
        [horizon, product_features["product_id"]], names=["date", "product_id"]
    ).to_frame(index=False)
    future_frame["forecast_units"] = product_features.set_index("product_id")[
        "avg_daily_units"
    ].reindex(future_frame["product_id"]).values

    expanded_promos = expanded_promos.rename(columns={"discount_pct": "planned_discount"})
    schedule = (
        future_frame.merge(expanded_promos, on=["date", "product_id"], how="left")
        .merge(
            product_features[
                [
                    "product_id",
                    "sku",
                    "name",
                    "category",
                    "unit_cost",
                    "unit_price",
                    "avg_lead_time_days",
                    "lead_time_std_days",
                    "min_order_qty",
                    "on_hand_units",
                    "on_order_units",
                    "reserved_units",
                    "safety_stock_units",
                ]
            ],
            on="product_id",
            how="left",
        )
        .sort_values(["product_id", "date"])
    )
    schedule["planned_discount"] = schedule["planned_discount"].fillna(0.0)
    schedule["promo_id"] = schedule["promo_id"].fillna("NONE")
    return schedule


def prepare_simulation_inputs(raw_frames: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Produce canonical inputs for the slow simulation engine and surrogate model.
    """

    from .transformations import build_planning_snapshot

    snapshot = build_planning_snapshot(raw_frames)
    expanded_promos = expand_promos(snapshot["promo_calendar"])
    schedule = build_simulation_schedule(
        snapshot["product_features"],
        snapshot["daily_demand"],
        expanded_promos,
    )

    return {
        "snapshot": snapshot,
        "expanded_promos": expanded_promos,
        "simulation_schedule": schedule,
    }


