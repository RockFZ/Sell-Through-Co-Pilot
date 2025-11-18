"""
Robyn-compatible marketing response stub.

Estimates promotional and advertising lift multipliers given synthetic data,
mirroring the structure of Meta Robyn outputs for development purposes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pandas as pd


@dataclass(frozen=True)
class RobynStubConfig:
    promo_discount_weight: float = 1.6
    ad_spend_weight: float = 0.0002
    ad_decay_half_life: int = 3


def _promo_lift(expanded_promos: pd.DataFrame, config: RobynStubConfig) -> pd.DataFrame:
    if expanded_promos.empty:
        return pd.DataFrame(columns=["date", "product_id", "promo_lift"])

    df = expanded_promos.copy()
    df["promo_lift"] = 1.0 + df["discount_pct"].fillna(0) * config.promo_discount_weight
    return df[["date", "product_id", "promo_lift"]]


def _ad_lift(ad_spend: pd.DataFrame, horizon_dates: pd.DatetimeIndex, config: RobynStubConfig) -> pd.DataFrame:
    if ad_spend.empty:
        return pd.DataFrame(
            {"date": horizon_dates, "ad_lift": [1.0] * len(horizon_dates)}
        )

    ad_df = ad_spend.copy()
    ad_df["date"] = pd.to_datetime(ad_df["date"])
    ad_df["lift"] = 1.0 + ad_df["planned_spend"] * config.ad_spend_weight
    ad_df = ad_df.groupby("date")["lift"].mean().reindex(horizon_dates, fill_value=1.0)

    # Apply simple exponential decay to mimic carryover
    ad_lift_values = []
    prev_lift = 1.0
    decay_factor = 0.5 ** (1 / config.ad_decay_half_life)
    for lift in ad_df.values:
        smoothed = max(prev_lift * decay_factor, 1.0)
        smoothed = max(smoothed, lift)
        ad_lift_values.append(smoothed)
        prev_lift = smoothed

    return pd.DataFrame({"date": horizon_dates, "ad_lift": ad_lift_values})


def build_lift_table(
    expanded_promos: pd.DataFrame,
    ad_spend: pd.DataFrame,
    products: pd.Index,
    horizon_dates: pd.DatetimeIndex,
    config: RobynStubConfig | None = None,
    historical_sales: pd.DataFrame | None = None,  # For compatibility
) -> pd.DataFrame:
    """
    Build a table of lift multipliers per product-date pair.
    """

    config = config or RobynStubConfig()

    promo_lift = _promo_lift(expanded_promos, config)
    ad_lift = _ad_lift(ad_spend, horizon_dates, config)

    base = pd.MultiIndex.from_product([horizon_dates, products], names=["date", "product_id"]).to_frame(
        index=False
    )
    base["promo_lift"] = 1.0
    base["ad_lift"] = 1.0

    if not promo_lift.empty:
        base = base.merge(promo_lift, on=["date", "product_id"], how="left", suffixes=("", "_promo"))
        base["promo_lift"] = base["promo_lift_promo"].fillna(base["promo_lift"])
        base = base.drop(columns=["promo_lift_promo"])

    if not ad_lift.empty:
        base = base.merge(ad_lift, on="date", how="left", suffixes=("", "_ad"))
        base["ad_lift"] = base["ad_lift_ad"].fillna(base["ad_lift"])
        base = base.drop(columns=["ad_lift_ad"])

    base["total_lift"] = base["promo_lift"] * base["ad_lift"]
    return base.sort_values(["product_id", "date"])

