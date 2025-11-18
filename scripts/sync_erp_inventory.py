#!/usr/bin/env python3
"""
Sync inventory from ERP systems (Odoo/ERPNext) to product features.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src import data_loader, transformations  # pylint: disable=wrong-import-position

# Try to import ERP clients
try:
    from src.erp import OdooClient, ERPNextClient, OdooConfig, ERPNextConfig
    ERP_AVAILABLE = True
except ImportError:
    ERP_AVAILABLE = False
    print("Warning: ERP modules not available")


def sync_odoo_inventory(product_features: pd.DataFrame, use_mock: bool = True) -> pd.DataFrame:
    """Sync inventory from Odoo."""
    if not ERP_AVAILABLE:
        print("ERP modules not available, skipping Odoo sync")
        return product_features
    
    print("Syncing inventory from Odoo...")
    odoo_config = OdooConfig(use_mock=use_mock)
    odoo_client = OdooClient(odoo_config)
    
    # Sync products that use Odoo (SKU-001, SKU-003)
    odoo_products = product_features[product_features["sku"].isin(["SKU-001", "SKU-003"])]
    if not odoo_products.empty:
        synced = odoo_client.sync_inventory_to_dataframe(odoo_products)
        # Merge back
        product_features = pd.concat([
            synced,
            product_features[~product_features["sku"].isin(["SKU-001", "SKU-003"])],
        ]).reset_index(drop=True)
        print(f"Synced {len(synced)} products from Odoo")
    else:
        print("No Odoo products found")
    
    return product_features


def sync_erpnext_inventory(product_features: pd.DataFrame, use_mock: bool = True) -> pd.DataFrame:
    """Sync inventory from ERPNext."""
    if not ERP_AVAILABLE:
        print("ERP modules not available, skipping ERPNext sync")
        return product_features
    
    print("Syncing inventory from ERPNext...")
    erpnext_config = ERPNextConfig(use_mock=use_mock)
    erpnext_client = ERPNextClient(erpnext_config)
    
    # Sync products that use ERPNext (SKU-002, SKU-004)
    erpnext_products = product_features[product_features["sku"].isin(["SKU-002", "SKU-004"])]
    if not erpnext_products.empty:
        synced = erpnext_client.sync_inventory_to_dataframe(erpnext_products)
        # Merge back
        product_features = pd.concat([
            synced,
            product_features[~product_features["sku"].isin(["SKU-002", "SKU-004"])],
        ]).reset_index(drop=True)
        print(f"Synced {len(synced)} products from ERPNext")
    else:
        print("No ERPNext products found")
    
    return product_features


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--erp-system",
        choices=["odoo", "erpnext", "all"],
        default="all",
        help="Which ERP system to sync from.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/product_features_synced.parquet"),
        help="Output path for synced product features.",
    )
    parser.add_argument(
        "--use-mock",
        action="store_true",
        default=True,
        help="Use mock data (default for MVP).",
    )
    parser.add_argument(
        "--no-mock",
        action="store_false",
        dest="use_mock",
        help="Use real ERP API (requires configured connection).",
    )
    args = parser.parse_args()
    
    # Load current product features
    raw_frames = data_loader.load_raw_frames()
    snapshot = transformations.build_planning_snapshot(raw_frames)
    product_features = snapshot["product_features"].copy()
    
    print(f"Starting with {len(product_features)} products")
    
    # Sync based on system choice
    if args.erp_system in ["odoo", "all"]:
        product_features = sync_odoo_inventory(product_features, use_mock=args.use_mock)
    
    if args.erp_system in ["erpnext", "all"]:
        product_features = sync_erpnext_inventory(product_features, use_mock=args.use_mock)
    
    # Save synced product features
    args.output.parent.mkdir(parents=True, exist_ok=True)
    product_features.to_parquet(args.output, index=False)
    
    print(f"\nSynced product features saved to {args.output}")
    print("\nInventory summary:")
    print(product_features[["sku", "name", "on_hand_units", "on_order_units", "reserved_units"]])


if __name__ == "__main__":
    main()


