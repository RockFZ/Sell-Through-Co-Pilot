"""
Feature engineering for surrogate model training and prediction.
"""

from __future__ import annotations

import pandas as pd


def prepare_training_features(
    simulation_logs: pd.DataFrame,
    product_features: pd.DataFrame,
    expanded_promos: pd.DataFrame,
    ad_spend: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepare features and targets from simulation logs for training.
    
    Args:
        simulation_logs: DataFrame with simulation results
        product_features: Product feature table
        expanded_promos: Promotional calendar
        ad_spend: Advertising spend data
        
    Returns:
        Tuple of (features_df, targets_df)
    """
    # Aggregate simulation logs to product-level outcomes
    product_outcomes = simulation_logs.groupby("product_id").agg({
        "projected_demand": "sum",
        "realized_demand": "sum",
        "lost_sales": "sum",
        "order_qty": "sum",
        "on_hand_start": "first",  # Initial inventory
        "safety_stock_units": "first",
    }).reset_index()
    
    # Calculate target metrics
    product_outcomes["service_level"] = (
        product_outcomes["realized_demand"] / product_outcomes["projected_demand"]
    ).fillna(1.0)
    product_outcomes["lost_sales_rate"] = (
        product_outcomes["lost_sales"] / product_outcomes["projected_demand"]
    ).fillna(0.0)
    
    # Merge with product features
    features = product_outcomes.merge(
        product_features,
        on="product_id",
        how="left",
    )
    
    # Add promo features (aggregate by product)
    if not expanded_promos.empty:
        promo_features = expanded_promos.groupby("product_id").agg({
            "discount_pct": ["mean", "max", "sum", "count"],
        }).reset_index()
        promo_features.columns = ["product_id", "avg_discount", "max_discount", "total_discount", "promo_days"]
        features = features.merge(promo_features, on="product_id", how="left")
        features["avg_discount"] = features["avg_discount"].fillna(0)
        features["max_discount"] = features["max_discount"].fillna(0)
        features["total_discount"] = features["total_discount"].fillna(0)
        features["promo_days"] = features["promo_days"].fillna(0)
    else:
        features["avg_discount"] = 0
        features["max_discount"] = 0
        features["total_discount"] = 0
        features["promo_days"] = 0
    
    # Add ad spend features
    if not ad_spend.empty:
        ad_features = ad_spend.groupby("date").agg({
            "planned_spend": "sum",
        }).reset_index()
        ad_features["total_ad_spend"] = ad_features["planned_spend"].sum()
        ad_features["avg_daily_ad_spend"] = ad_features["planned_spend"].mean()
        # Add as constant features (same for all products)
        features["total_ad_spend"] = ad_features["total_ad_spend"].iloc[0] if len(ad_features) > 0 else 0
        features["avg_daily_ad_spend"] = ad_features["avg_daily_ad_spend"].iloc[0] if len(ad_features) > 0 else 0
    else:
        features["total_ad_spend"] = 0
        features["avg_daily_ad_spend"] = 0
    
    # Select feature columns (exclude targets and IDs)
    feature_cols = [
        # Product features
        "unit_cost", "unit_price", "case_pack", "min_inventory", "max_inventory",
        "avg_daily_units", "std_daily_units", "avg_lead_time_days", "lead_time_std_days",
        "min_order_qty", "on_hand_units", "on_order_units", "reserved_units",
        "safety_stock_units", "return_rate",
        # Promo features
        "avg_discount", "max_discount", "total_discount", "promo_days",
        # Ad features
        "total_ad_spend", "avg_daily_ad_spend",
        # Initial state
        "on_hand_start",
    ]
    
    # Filter to available columns
    available_cols = [col for col in feature_cols if col in features.columns]
    X = features[["product_id"] + available_cols].copy()
    
    # Fill missing values
    X = X.fillna(0)
    
    # Target columns
    target_cols = [
        "realized_demand",
        "lost_sales",
        "service_level",
        "lost_sales_rate",
        "order_qty",
    ]
    y = features[["product_id"] + [col for col in target_cols if col in features.columns]].copy()
    
    return X, y


def prepare_prediction_features(
    product_features: pd.DataFrame,
    expanded_promos: pd.DataFrame,
    ad_spend: pd.DataFrame,
    initial_inventory: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Prepare features for prediction (without simulation outcomes).
    
    Args:
        product_features: Product feature table
        expanded_promos: Promotional calendar
        ad_spend: Advertising spend data
        initial_inventory: Optional initial inventory override
        
    Returns:
        DataFrame with features ready for prediction
    """
    features = product_features.copy()
    
    # Add initial inventory if provided
    if initial_inventory is not None:
        features = features.merge(
            initial_inventory[["product_id", "on_hand_units"]],
            on="product_id",
            how="left",
            suffixes=("", "_init"),
        )
        features["on_hand_start"] = features["on_hand_units_init"].fillna(features["on_hand_units"])
    else:
        features["on_hand_start"] = features["on_hand_units"]
    
    # Add promo features
    if not expanded_promos.empty:
        promo_features = expanded_promos.groupby("product_id").agg({
            "discount_pct": ["mean", "max", "sum", "count"],
        }).reset_index()
        promo_features.columns = ["product_id", "avg_discount", "max_discount", "total_discount", "promo_days"]
        features = features.merge(promo_features, on="product_id", how="left")
        features["avg_discount"] = features["avg_discount"].fillna(0)
        features["max_discount"] = features["max_discount"].fillna(0)
        features["total_discount"] = features["total_discount"].fillna(0)
        features["promo_days"] = features["promo_days"].fillna(0)
    else:
        features["avg_discount"] = 0
        features["max_discount"] = 0
        features["total_discount"] = 0
        features["promo_days"] = 0
    
    # Add ad spend features
    if not ad_spend.empty:
        ad_features = ad_spend.groupby("date").agg({
            "planned_spend": "sum",
        }).reset_index()
        total_ad = ad_features["planned_spend"].sum()
        avg_ad = ad_features["planned_spend"].mean()
        features["total_ad_spend"] = total_ad
        features["avg_daily_ad_spend"] = avg_ad
    else:
        features["total_ad_spend"] = 0
        features["avg_daily_ad_spend"] = 0
    
    # Fill missing values
    features = features.fillna(0)
    
    return features

