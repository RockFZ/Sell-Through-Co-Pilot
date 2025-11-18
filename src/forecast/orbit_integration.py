"""
Real Uber Orbit integration with fallback to enhanced stub.

Attempts to use orbit-ml library if available, otherwise falls back to
an enhanced exponential smoothing implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd

# Try to import Orbit, fallback to None if not available
try:
    from orbit.models import DLT
    ORBIT_AVAILABLE = True
except ImportError:
    ORBIT_AVAILABLE = False
    DLT = None


@dataclass(frozen=True)
class OrbitConfig:
    """Configuration for Orbit forecasting."""
    horizon_days: int = 30
    seasonality: list[int] = None  # e.g., [7] for weekly
    prediction_percentiles: list[float] = None  # e.g., [10, 50, 90]
    use_real_orbit: bool = True  # Set to False to force stub


def _enhanced_exponential_smoothing_forecast(
    history: pd.DataFrame, config: OrbitConfig
) -> pd.DataFrame:
    """
    Enhanced exponential smoothing with trend and seasonality detection.
    Used as fallback when Orbit is not available.
    """
    history = history.sort_values("date").copy()
    history["date"] = pd.to_datetime(history["date"])
    
    # Aggregate by date if multiple channels
    if "channel" in history.columns:
        history = history.groupby("date")["units_sold"].sum().reset_index()
    
    series = history.set_index("date")["units_sold"]
    
    # Detect weekly seasonality
    if len(series) >= 14:
        weekly_avg = series.groupby(series.index.dayofweek).mean()
        seasonal_factor = weekly_avg / weekly_avg.mean()
    else:
        seasonal_factor = pd.Series([1.0] * 7, index=range(7))
    
    # Exponential smoothing with trend
    alpha = 0.3
    beta = 0.1
    level = series.iloc[0]
    trend = 0.0
    
    for i in range(1, len(series)):
        prev_level = level
        level = alpha * series.iloc[i] + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend
    
    # Forecast
    forecast_dates = pd.date_range(
        series.index.max() + pd.Timedelta(days=1),
        periods=config.horizon_days,
        freq="D",
    )
    
    # Calculate residuals for uncertainty
    fitted = []
    temp_level = series.iloc[0]
    temp_trend = 0.0
    for i in range(len(series)):
        day_of_week = series.index[i].dayofweek
        seasonal = seasonal_factor[day_of_week]
        fitted.append(temp_level * seasonal)
        prev_level = temp_level
        temp_level = alpha * (series.iloc[i] / seasonal) + (1 - alpha) * (temp_level + temp_trend)
        temp_trend = beta * (temp_level - prev_level) + (1 - beta) * temp_trend
    
    residuals = series.values - np.array(fitted)
    residual_std = np.std(residuals) if len(residuals) > 1 else 1.0
    
    # Generate forecasts
    forecast_values = []
    current_level = level
    current_trend = trend
    
    for date in forecast_dates:
        day_of_week = date.dayofweek
        seasonal = seasonal_factor[day_of_week]
        forecast_values.append(current_level * seasonal)
        current_level = current_level + current_trend
    
    forecast_values = np.array(forecast_values)
    
    # Prediction intervals (80% = 1.28 * std)
    interval_width = 1.28 * residual_std
    
    return pd.DataFrame({
        "date": forecast_dates,
        "forecast_units": forecast_values,
        "forecast_lower": np.clip(forecast_values - interval_width, a_min=0, a_max=None),
        "forecast_upper": forecast_values + interval_width,
    })


def _orbit_forecast(
    history: pd.DataFrame, config: OrbitConfig
) -> pd.DataFrame:
    """
    Use real Uber Orbit DLT model for forecasting.
    """
    history = history.sort_values("date").copy()
    history["date"] = pd.to_datetime(history["date"])
    
    # Aggregate by date if multiple channels
    if "channel" in history.columns:
        history = history.groupby("date")["units_sold"].sum().reset_index()
    
    # Prepare data for Orbit
    orbit_df = history[["date", "units_sold"]].copy()
    orbit_df = orbit_df.rename(columns={"units_sold": "response"})
    
    # Configure seasonality
    seasonality = config.seasonality or []
    if len(orbit_df) >= 14 and 7 not in seasonality:
        # Auto-detect weekly seasonality if enough data
        seasonality = [7]
    
    # Fit DLT model
    model = DLT(
        response_col="response",
        date_col="date",
        seasonality=seasonality if seasonality else None,
        prediction_percentiles=config.prediction_percentiles or [10, 50, 90],
    )
    model.fit(df=orbit_df)
    
    # Generate forecasts
    forecast_df = model.predict(df=orbit_df)
    
    # Rename columns to match expected format
    forecast_df = forecast_df.rename(columns={
        "prediction": "forecast_units",
        "prediction_10": "forecast_lower",
        "prediction_90": "forecast_upper",
    })
    
    # Ensure we have the right columns
    if "forecast_units" not in forecast_df.columns and "prediction_50" in forecast_df.columns:
        forecast_df["forecast_units"] = forecast_df["prediction_50"]
    
    return forecast_df[["date", "forecast_units", "forecast_lower", "forecast_upper"]]


def forecast_product(
    history: pd.DataFrame, config: OrbitConfig
) -> pd.DataFrame:
    """
    Produce forecasts for a single product.
    Uses real Orbit if available, otherwise enhanced stub.
    """
    if len(history) < 3:
        # Not enough data, return flat forecast
        forecast_dates = pd.date_range(
            pd.to_datetime(history["date"]).max() + pd.Timedelta(days=1),
            periods=config.horizon_days,
            freq="D",
        )
        avg_demand = history["units_sold"].mean() if len(history) > 0 else 1.0
        return pd.DataFrame({
            "date": forecast_dates,
            "forecast_units": [avg_demand] * config.horizon_days,
            "forecast_lower": [max(0, avg_demand * 0.7)] * config.horizon_days,
            "forecast_upper": [avg_demand * 1.3] * config.horizon_days,
        })
    
    use_real = config.use_real_orbit and ORBIT_AVAILABLE
    
    if use_real:
        try:
            return _orbit_forecast(history, config)
        except Exception as e:
            # Fallback to stub if Orbit fails
            print(f"Warning: Orbit forecast failed, using fallback: {e}")
            return _enhanced_exponential_smoothing_forecast(history, config)
    else:
        return _enhanced_exponential_smoothing_forecast(history, config)


def forecast_bundle(
    daily_demand: pd.DataFrame,
    config: OrbitConfig | None = None,
) -> Dict[str, pd.DataFrame]:
    """
    Generate forecasts for all products.
    
    Args:
        daily_demand: DataFrame with columns [date, product_id, units_sold, ...]
        config: Orbit configuration
        
    Returns:
        Dictionary mapping product_id to forecast DataFrame
    """
    config = config or OrbitConfig()
    forecasts: Dict[str, pd.DataFrame] = {}
    
    for product_id, group in daily_demand.groupby("product_id"):
        forecasts[product_id] = forecast_product(group, config)
    
    return forecasts


