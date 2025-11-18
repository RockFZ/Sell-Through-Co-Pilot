"""
Orbit-compatible demand forecasting stub.

Provides a lightweight exponential smoothing baseline to emulate Uber Orbit's
daily forecast interface for development and testing purposes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class OrbitStubConfig:
    horizon_days: int = 30
    alpha: float = 0.35
    interval_width: float = 1.28  # approx 80% interval


def _simple_exponential_smoothing(series: pd.Series, alpha: float) -> float:
    smoothed = series.iloc[0]
    for value in series.iloc[1:]:
        smoothed = alpha * value + (1 - alpha) * smoothed
    return smoothed


def forecast_product(
    history: pd.DataFrame, config: OrbitStubConfig
) -> pd.DataFrame:
    """Produce forecasts for a single product from historical demand."""

    history = history.sort_values("date")
    smoothed_level = _simple_exponential_smoothing(history["units_sold"], config.alpha)
    residuals = history["units_sold"] - history["units_sold"].rolling(7, min_periods=1).mean()
    residual_std = residuals.std(ddof=0) if len(residuals) > 1 else 1.0

    forecast_dates = pd.date_range(
        history["date"].max() + pd.Timedelta(days=1),
        periods=config.horizon_days,
        freq="D",
    )
    forecast_values = np.full(config.horizon_days, smoothed_level)
    intervals = config.interval_width * residual_std

    return pd.DataFrame(
        {
            "date": forecast_dates,
            "forecast_units": forecast_values,
            "forecast_lower": np.clip(forecast_values - intervals, a_min=0, a_max=None),
            "forecast_upper": forecast_values + intervals,
        }
    )


def forecast_bundle(
    daily_demand: pd.DataFrame,
    config: OrbitStubConfig | None = None,
    **kwargs,  # For compatibility with orbit_integration signature
) -> Dict[str, pd.DataFrame]:
    """
    Generate a dictionary of forecasts keyed by product_id.
    """

    config = config or OrbitStubConfig()
    forecasts: Dict[str, pd.DataFrame] = {}

    for product_id, group in daily_demand.groupby("product_id"):
        if len(group) < 3:
            continue
        forecasts[product_id] = forecast_product(group, config)

    return forecasts

