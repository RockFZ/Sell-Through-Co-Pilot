"""
Transform raw datasets into simulation-ready feature tables.
"""

from __future__ import annotations

from typing import Dict

import pandas as pd


def compute_daily_demand(raw_frames: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Aggregate sales history to daily demand by product and channel.
    """

    sales = raw_frames["sales_history"].copy()
    sales["date"] = pd.to_datetime(sales["date"])
    demand = (
        sales.groupby(["date", "product_id", "channel"], as_index=False)["units_sold"]
        .sum()
        .sort_values(["product_id", "date"])
    )
    return demand


def compute_returns_summary(raw_frames: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    returns = raw_frames["returns"].copy()
    returns["date"] = pd.to_datetime(returns["date"])
    summary = (
        returns.groupby(["product_id"], as_index=False)["units_returned"]
        .sum()
        .rename(columns={"units_returned": "total_units_returned"})
    )
    return summary


def compute_product_features(raw_frames: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Combine products, demand, returns, and lead-times into a canonical feature table.
    """

    products = raw_frames["products"].copy()
    demand = compute_daily_demand(raw_frames)
    returns_summary = compute_returns_summary(raw_frames)
    lead_times = raw_frames["lead_times"].copy()
    inventory = raw_frames["current_inventory"].copy()

    demand_stats = (
        demand.groupby("product_id")["units_sold"]
        .agg(["mean", "std", "max", "min"])
        .reset_index()
        .rename(
            columns={
                "mean": "avg_daily_units",
                "std": "std_daily_units",
                "max": "max_daily_units",
                "min": "min_daily_units",
            }
        )
    )

    merged = (
        products.merge(demand_stats, on="product_id", how="left")
        .merge(returns_summary, on="product_id", how="left")
        .merge(lead_times, on="product_id", how="left")
        .merge(inventory, on="product_id", how="left")
    )
    merged["return_rate"] = merged["total_units_returned"].fillna(0) / (
        merged["avg_daily_units"].clip(lower=1)
    )
    merged["safety_stock_units"] = (
        merged["avg_daily_units"].fillna(0) * merged["avg_lead_time_days"].fillna(0)
    )
    return merged


def build_planning_snapshot(raw_frames: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Produce a bundle of processed tables used for downstream engines.
    """

    return {
        "daily_demand": compute_daily_demand(raw_frames),
        "product_features": compute_product_features(raw_frames),
        "promo_calendar": raw_frames["promo_calendar"].copy(),
        "ad_spend": raw_frames["ad_spend"].copy(),
    }


