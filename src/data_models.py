"""
Typed data models for the core Sell-Through Co-Pilot datasets.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

Channel = Literal["web", "store"]


@dataclass(frozen=True)
class Product:
    product_id: str
    sku: str
    name: str
    category: str
    unit_cost: float
    unit_price: float
    case_pack: int
    min_inventory: int
    max_inventory: int


@dataclass(frozen=True)
class Sale:
    date: date
    product_id: str
    units_sold: int
    channel: Channel


@dataclass(frozen=True)
class Return:
    date: date
    product_id: str
    units_returned: int
    reason: str


@dataclass(frozen=True)
class LeadTime:
    product_id: str
    supplier_id: str
    supplier_name: str
    avg_lead_time_days: float
    lead_time_std_days: float
    min_order_qty: int


@dataclass(frozen=True)
class Promo:
    promo_id: str
    start_date: date
    end_date: date
    product_id: str
    discount_pct: float
    description: str


@dataclass(frozen=True)
class AdSpend:
    date: date
    channel: str
    planned_spend: float
    product_focus: str


@dataclass(frozen=True)
class InventorySnapshot:
    product_id: str
    on_hand_units: int
    on_order_units: int
    reserved_units: int
    warehouse: str


