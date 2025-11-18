"""
Dashboard with readiness light and risk timeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class RiskThresholds:
    """Thresholds for risk assessment."""
    service_level_warning: float = 0.95  # Below this is warning
    service_level_critical: float = 0.90  # Below this is critical
    lost_sales_rate_warning: float = 0.05  # Above this is warning
    lost_sales_rate_critical: float = 0.10  # Above this is critical
    inventory_days_warning: float = 7.0  # Below this is warning
    inventory_days_critical: float = 3.0  # Below this is critical


class Dashboard:
    """
    Dashboard showing readiness status and risk timeline.
    """
    
    def __init__(self, risk_thresholds: RiskThresholds | None = None):
        self.risk_thresholds = risk_thresholds or RiskThresholds()
        self.predictions: Optional[pd.DataFrame] = None
        self.product_features: Optional[pd.DataFrame] = None
        self.risk_timeline: Optional[pd.DataFrame] = None
    
    def calculate_readiness(
        self,
        predictions: pd.DataFrame,
        product_features: pd.DataFrame,
    ) -> Dict[str, str]:
        """
        Calculate readiness status (green/yellow/red) for each product.
        
        Args:
            predictions: Surrogate model predictions
            product_features: Product features including inventory
            
        Returns:
            Dictionary mapping product_id to status ("green", "yellow", "red")
        """
        # Merge predictions with product features
        merged = predictions.merge(
            product_features[["product_id", "on_hand_units", "avg_daily_units"]],
            on="product_id",
            how="left",
        )
        
        # Calculate inventory days
        merged["inventory_days"] = (
            merged["on_hand_units"] / merged["avg_daily_units"].clip(lower=0.1)
        )
        
        readiness = {}
        
        for _, row in merged.iterrows():
            product_id = row["product_id"]
            service_level = row.get("service_level", 1.0)
            lost_sales_rate = row.get("lost_sales_rate", 0.0)
            inventory_days = row.get("inventory_days", 0.0)
            
            # Determine status
            status = "green"
            
            # Check critical conditions
            if (
                service_level < self.risk_thresholds.service_level_critical
                or lost_sales_rate > self.risk_thresholds.lost_sales_rate_critical
                or inventory_days < self.risk_thresholds.inventory_days_critical
            ):
                status = "red"
            # Check warning conditions
            elif (
                service_level < self.risk_thresholds.service_level_warning
                or lost_sales_rate > self.risk_thresholds.lost_sales_rate_warning
                or inventory_days < self.risk_thresholds.inventory_days_warning
            ):
                status = "yellow"
            
            readiness[product_id] = status
        
        return readiness
    
    def calculate_risk_timeline(
        self,
        simulation_logs: pd.DataFrame,
        product_features: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Calculate risk metrics over time.
        
        Args:
            simulation_logs: Day-by-day simulation results
            product_features: Product features
            
        Returns:
            DataFrame with risk metrics by date and product
        """
        # Merge with product features for context
        merged = simulation_logs.merge(
            product_features[["product_id", "avg_daily_units", "safety_stock_units"]],
            on="product_id",
            how="left",
        )
        
        # Calculate risk metrics
        merged["service_level"] = (
            merged["realized_demand"] / merged["projected_demand"].clip(lower=0.1)
        )
        merged["lost_sales_rate"] = (
            merged["lost_sales"] / merged["projected_demand"].clip(lower=0.1)
        )
        merged["inventory_days"] = (
            merged["on_hand_end"] / merged["avg_daily_units"].clip(lower=0.1)
        )
        merged["below_safety_stock"] = (
            merged["on_hand_end"] < merged["safety_stock_units"]
        ).astype(int)
        
        # Calculate risk score (0-100, higher is worse)
        merged["risk_score"] = (
            (1 - merged["service_level"]) * 40
            + merged["lost_sales_rate"] * 30
            + (merged["inventory_days"] < 7).astype(int) * 20
            + merged["below_safety_stock"] * 10
        ).clip(0, 100)
        
        # Determine risk level
        merged["risk_level"] = merged["risk_score"].apply(
            lambda x: "critical" if x > 50 else ("warning" if x > 25 else "low")
        )
        
        return merged[
            [
                "product_id",
                "date",
                "service_level",
                "lost_sales_rate",
                "inventory_days",
                "below_safety_stock",
                "risk_score",
                "risk_level",
            ]
        ].sort_values(["product_id", "date"])
    
    def generate_dashboard_data(
        self,
        predictions: pd.DataFrame,
        product_features: pd.DataFrame,
        simulation_logs: pd.DataFrame | None = None,
    ) -> Dict:
        """
        Generate complete dashboard data.
        
        Args:
            predictions: Surrogate model predictions
            product_features: Product features
            simulation_logs: Optional simulation logs for timeline
            
        Returns:
            Dictionary with dashboard data
        """
        # Calculate readiness
        readiness = self.calculate_readiness(predictions, product_features)
        
        # Calculate overall readiness (worst status)
        overall_status = "green"
        if "red" in readiness.values():
            overall_status = "red"
        elif "yellow" in readiness.values():
            overall_status = "yellow"
        
        # Calculate risk timeline if simulation logs provided
        risk_timeline = None
        if simulation_logs is not None:
            risk_timeline = self.calculate_risk_timeline(simulation_logs, product_features)
        
        # Aggregate metrics
        summary = {
            "overall_status": overall_status,
            "products": [],
        }
        
        for product_id, status in readiness.items():
            product_pred = predictions[predictions["product_id"] == product_id].iloc[0]
            product_feat = product_features[product_features["product_id"] == product_id].iloc[0]
            
            product_data = {
                "product_id": product_id,
                "name": product_feat.get("name", product_id),
                "status": status,
                "service_level": float(product_pred.get("service_level", 1.0)),
                "lost_sales_rate": float(product_pred.get("lost_sales_rate", 0.0)),
                "predicted_realized_demand": float(product_pred.get("realized_demand", 0.0)),
                "predicted_lost_sales": float(product_pred.get("lost_sales", 0.0)),
            }
            summary["products"].append(product_data)
        
        dashboard_data = {
            "readiness": {
                "overall_status": overall_status,
                "products": summary["products"],
            },
            "risk_timeline": risk_timeline.to_dict(orient="records") if risk_timeline is not None else None,
        }
        
        return dashboard_data
    
    def save_dashboard(self, dashboard_data: Dict, output_path: Path) -> None:
        """Save dashboard data to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(dashboard_data, indent=2, default=str))


def create_dashboard(
    predictions: pd.DataFrame,
    product_features: pd.DataFrame,
    simulation_logs: pd.DataFrame | None = None,
    risk_thresholds: RiskThresholds | None = None,
) -> Dashboard:
    """
    Create and populate dashboard.
    
    Args:
        predictions: Surrogate model predictions
        product_features: Product features
        simulation_logs: Optional simulation logs
        risk_thresholds: Risk threshold configuration
        
    Returns:
        Dashboard instance
    """
    dashboard = Dashboard(risk_thresholds)
    dashboard.predictions = predictions
    dashboard.product_features = product_features
    
    if simulation_logs is not None:
        dashboard.risk_timeline = dashboard.calculate_risk_timeline(
            simulation_logs, product_features
        )
    
    return dashboard

