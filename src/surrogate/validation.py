"""
Validation utilities for surrogate model.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd

from .model import SurrogateModel


def validate_on_holdout(
    model: SurrogateModel,
    X_test: pd.DataFrame,
    y_test: pd.DataFrame,
    simulation_logs_test: pd.DataFrame | None = None,
) -> Dict[str, Dict]:
    """
    Validate surrogate model on hold-out test set.
    
    Args:
        model: Trained surrogate model
        X_test: Test features
        y_test: Test targets (ground truth)
        simulation_logs_test: Optional full simulation logs for detailed analysis
        
    Returns:
        Dictionary of validation metrics per target
    """
    # Predict
    y_pred = model.predict(X_test)
    
    # Calculate metrics for each target
    metrics = {}
    
    for target_name in model.target_names:
        if target_name not in y_test.columns or target_name not in y_pred.columns:
            continue
        
        y_true = y_test[target_name].values
        y_pred_values = y_pred[target_name].values
        
        # Calculate metrics
        mae = float(pd.Series(y_true - y_pred_values).abs().mean())
        rmse = float(((y_true - y_pred_values) ** 2).mean() ** 0.5)
        
        # R² score
        ss_res = ((y_true - y_pred_values) ** 2).sum()
        ss_tot = ((y_true - y_true.mean()) ** 2).sum()
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        # Mean absolute percentage error (for non-zero targets)
        mask = y_true != 0
        mape = float((pd.Series((y_true[mask] - y_pred_values[mask]) / y_true[mask]).abs().mean() * 100)) if mask.sum() > 0 else 0.0
        
        metrics[target_name] = {
            "mae": mae,
            "rmse": rmse,
            "r2": float(r2),
            "mape": mape,
            "n_samples": len(y_true),
        }
    
    return metrics


def compare_surrogate_vs_simulation(
    surrogate_predictions: pd.DataFrame,
    simulation_results: pd.DataFrame,
) -> Dict[str, Dict]:
    """
    Compare surrogate predictions with full simulation results.
    
    Args:
        surrogate_predictions: Predictions from surrogate model
        simulation_results: Results from full simulation
        
    Returns:
        Comparison metrics
    """
    # Aggregate simulation results to product level
    sim_agg = simulation_results.groupby("product_id").agg({
        "realized_demand": "sum",
        "lost_sales": "sum",
        "projected_demand": "sum",
        "order_qty": "sum",
    }).reset_index()
    
    sim_agg["service_level"] = sim_agg["realized_demand"] / sim_agg["projected_demand"]
    sim_agg["lost_sales_rate"] = sim_agg["lost_sales"] / sim_agg["projected_demand"]
    
    # Merge predictions
    comparison = surrogate_predictions.merge(
        sim_agg,
        on="product_id",
        how="inner",
        suffixes=("_pred", "_sim"),
    )
    
    metrics = {}
    
    for target in ["realized_demand", "lost_sales", "service_level", "lost_sales_rate", "order_qty"]:
        if f"{target}_pred" not in comparison.columns or f"{target}_sim" not in comparison.columns:
            continue
        
        pred_col = f"{target}_pred"
        sim_col = f"{target}_sim"
        
        mae = float((comparison[pred_col] - comparison[sim_col]).abs().mean())
        rmse = float(((comparison[pred_col] - comparison[sim_col]) ** 2).mean() ** 0.5)
        
        # Correlation
        corr = float(comparison[[pred_col, sim_col]].corr().iloc[0, 1])
        
        metrics[target] = {
            "mae": mae,
            "rmse": rmse,
            "correlation": corr,
            "n_products": len(comparison),
        }
    
    return metrics

