"""
Data validation helpers for Sell-Through Co-Pilot.
"""

from __future__ import annotations

from typing import Dict

import pandas as pd

from . import config

EXPECTED_FILES: Dict[str, Dict[str, str]] = {
    "products": {
        "path": (config.DATA_PATHS.raw_dir / "products.csv").as_posix(),
        "columns": [
            "product_id",
            "sku",
            "name",
            "category",
            "unit_cost",
            "unit_price",
            "case_pack",
            "min_inventory",
            "max_inventory",
        ],
    },
    "sales_history": {
        "path": (config.DATA_PATHS.raw_dir / "sales_history.csv").as_posix(),
        "columns": ["date", "product_id", "units_sold", "channel"],
    },
    "returns": {
        "path": (config.DATA_PATHS.raw_dir / "returns.csv").as_posix(),
        "columns": ["date", "product_id", "units_returned", "reason"],
    },
    "lead_times": {
        "path": (config.DATA_PATHS.raw_dir / "lead_times.csv").as_posix(),
        "columns": [
            "product_id",
            "supplier_id",
            "supplier_name",
            "avg_lead_time_days",
            "lead_time_std_days",
            "min_order_qty",
        ],
    },
    "promo_calendar": {
        "path": (config.DATA_PATHS.raw_dir / "promo_calendar.csv").as_posix(),
        "columns": [
            "promo_id",
            "start_date",
            "end_date",
            "product_id",
            "discount_pct",
            "description",
        ],
    },
    "ad_spend": {
        "path": (config.DATA_PATHS.raw_dir / "ad_spend.csv").as_posix(),
        "columns": ["date", "channel", "planned_spend", "product_focus"],
    },
    "current_inventory": {
        "path": (config.DATA_PATHS.raw_dir / "current_inventory.csv").as_posix(),
        "columns": [
            "product_id",
            "on_hand_units",
            "on_order_units",
            "reserved_units",
            "warehouse",
        ],
    },
}


def assert_expected_columns(df: pd.DataFrame, expected_cols: list[str], name: str) -> None:
    """Ensure a dataframe matches the expected column set."""

    actual_cols = list(df.columns)
    if actual_cols != expected_cols:
        raise ValueError(
            f"{name}: expected columns {expected_cols}, but received {actual_cols}"
        )


def check_for_missing_products(df: pd.DataFrame, product_ids: set[str], name: str) -> None:
    """Validate that the dataframe does not introduce unknown product IDs."""

    unknown = set(df["product_id"].unique()) - product_ids
    if unknown:
        raise ValueError(f"{name}: unknown product_ids detected: {sorted(unknown)}")


def run_basic_validations(raw_frames: Dict[str, pd.DataFrame]) -> None:
    """
    Run minimal structural checks across the raw dataset bundle.
    """

    products = raw_frames["products"]
    product_ids = set(products["product_id"].unique())

    for name, cfg in EXPECTED_FILES.items():
        assert_expected_columns(raw_frames[name], cfg["columns"], name)

    for name in ("sales_history", "returns", "lead_times", "promo_calendar", "current_inventory"):
        check_for_missing_products(raw_frames[name], product_ids, name)

    if raw_frames["sales_history"]["units_sold"].lt(0).any():
        raise ValueError("sales_history: negative units_sold detected")

    if raw_frames["returns"]["units_returned"].lt(0).any():
        raise ValueError("returns: negative units_returned detected")

    if raw_frames["ad_spend"]["planned_spend"].lt(0).any():
        raise ValueError("ad_spend: negative planned_spend detected")

    if raw_frames["promo_calendar"]["discount_pct"].gt(1).any():
        raise ValueError("promo_calendar: discount_pct greater than 1 detected")


