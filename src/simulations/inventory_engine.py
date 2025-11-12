"""
Inventory simulation engine inspired by Odoo/ERPNext reorder rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

import pandas as pd


@dataclass(frozen=True)
class SimulationConfig:
    reorder_policy: str = "min_max"
    service_level_multiplier: float = 1.0
    max_backlog_days: int = 7


def _initialize_state(product_row: pd.Series) -> Dict[str, float]:
    return {
        "on_hand": float(product_row.get("on_hand_units", 0)),
        "in_transit": float(product_row.get("on_order_units", 0)),
        "reserved": float(product_row.get("reserved_units", 0)),
        "backlog": 0.0,
    }


def _calculate_reorder_quantity(product_row: pd.Series, state: Dict[str, float]) -> float:
    min_inv = float(product_row.get("min_inventory", 0))
    max_inv = float(product_row.get("max_inventory", min_inv))

    projected_available = state["on_hand"] + state["in_transit"] - state["backlog"]
    if projected_available > min_inv:
        return 0.0

    target = max_inv
    order_qty = target - projected_available
    case_pack = max(int(product_row.get("case_pack", 1)), 1)
    min_order_qty = max(int(product_row.get("min_order_qty", case_pack)), case_pack)

    order_qty = max(order_qty, min_order_qty)
    # Round up to nearest case pack
    remainder = order_qty % case_pack
    if remainder:
        order_qty += case_pack - remainder

    return max(order_qty, 0.0)


def run_inventory_simulation(
    schedule: pd.DataFrame,
    product_features: pd.DataFrame,
    lifts: pd.DataFrame,
    forecasts: Dict[str, pd.DataFrame],
    config: SimulationConfig | None = None,
) -> pd.DataFrame:
    """
    Simulate inventory positions using Orbit + Robyn stubs and min-max rules.
    """

    config = config or SimulationConfig()
    results = []
    product_lookup = product_features.set_index("product_id")
    lift_lookup = (
        lifts.set_index(["product_id", "date"])
        if not lifts.empty
        else pd.DataFrame(columns=["total_lift"]).set_index(["product_id", "date"])
    )

    for product_id, product_schedule in schedule.groupby("product_id"):
        if product_id not in forecasts:
            continue

        product_row = product_lookup.loc[product_id]
        state = _initialize_state(product_row)

        # outstanding orders arrival queue
        arrivals: Dict[pd.Timestamp, float] = {}
        lead_time = int(round(product_row.get("avg_lead_time_days", 7)))
        safety_stock = float(product_row.get("safety_stock_units", 0))

        product_forecast = forecasts[product_id].set_index("date")

        for _, row in product_schedule.iterrows():
            date = row["date"]
            forecast_row = product_forecast.loc[date]
            lift_row = lift_lookup.loc[(product_id, date)] if (product_id, date) in lift_lookup.index else {}
            total_lift = float(lift_row.get("total_lift", 1.0))
            projected_demand = forecast_row["forecast_units"] * total_lift

            on_hand_start = state["on_hand"]

            # Receive orders arriving today
            inbound = arrivals.pop(date, 0.0)
            if inbound:
                state["on_hand"] += inbound
                state["in_transit"] -= inbound

            available_for_sale = max(state["on_hand"] - state["reserved"], 0.0)
            realized_demand = min(available_for_sale, projected_demand)
            lost_sales = max(projected_demand - available_for_sale, 0.0)

            state["on_hand"] = available_for_sale - realized_demand + state["reserved"]

            # Update backlog (assume lost sales become backlog up to max_backlog_days)
            state["backlog"] = min(
                state["backlog"] + lost_sales,
                projected_demand * config.max_backlog_days,
            )

            order_qty = _calculate_reorder_quantity(product_row, state)
            if order_qty > 0:
                arrival_date = date + pd.Timedelta(days=lead_time)
                arrivals[arrival_date] = arrivals.get(arrival_date, 0.0) + order_qty
                state["in_transit"] += order_qty

            results.append(
                {
                    "product_id": product_id,
                    "date": date,
                    "on_hand_start": on_hand_start,
                    "inbound_units": inbound,
                    "realized_demand": realized_demand,
                    "projected_demand": projected_demand,
                    "lost_sales": lost_sales,
                    "on_hand_end": state["on_hand"],
                    "backlog_units": state["backlog"],
                    "order_qty": order_qty,
                    "safety_stock_units": safety_stock,
                }
            )

    return pd.DataFrame(results).sort_values(["product_id", "date"])

