"""
Odoo ERP integration client.

Supports both real Odoo XML-RPC API and mock mode for development.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

# Try to import xmlrpc, fallback to mock
try:
    import xmlrpc.client
    XMLRPC_AVAILABLE = True
except ImportError:
    XMLRPC_AVAILABLE = False
    xmlrpc = None


@dataclass
class OdooConfig:
    """Configuration for Odoo connection."""
    url: str = "http://localhost:8069"
    db: str = "sellthrough"
    username: str = "admin"
    password: str = "admin"
    use_mock: bool = False  # Set to True to use mock data


class OdooClient:
    """
    Client for interacting with Odoo ERP system.
    
    Supports both real API calls and mock mode for development/testing.
    """
    
    def __init__(self, config: OdooConfig | None = None):
        self.config = config or OdooConfig()
        self.uid = None
        self.models = None
        
        if not self.config.use_mock and XMLRPC_AVAILABLE:
            try:
                common = xmlrpc.client.ServerProxy(f"{self.config.url}/xmlrpc/2/common")
                self.uid = common.authenticate(
                    self.config.db,
                    self.config.username,
                    self.config.password,
                    {}
                )
                if self.uid:
                    self.models = xmlrpc.client.ServerProxy(f"{self.config.url}/xmlrpc/2/object")
            except Exception as e:
                print(f"Warning: Could not connect to Odoo, using mock mode: {e}")
                self.config.use_mock = True
    
    def _mock_product_inventory(self, product_sku: str) -> Dict:
        """Mock inventory data for development."""
        # Return mock data based on SKU
        mock_data = {
            "SKU-001": {"qty_available": 85, "incoming_qty": 20, "outgoing_qty": 5},
            "SKU-003": {"qty_available": 45, "incoming_qty": 0, "outgoing_qty": 2},
        }
        return mock_data.get(product_sku, {"qty_available": 50, "incoming_qty": 0, "outgoing_qty": 0})
    
    def _mock_reorder_suggestions(self) -> List[Dict]:
        """Mock reorder suggestions for development."""
        return [
            {
                "product_id": [1, "SKU-001"],
                "qty_min": 40,
                "qty_max": 160,
                "qty_to_order": 120,
            },
            {
                "product_id": [3, "SKU-003"],
                "qty_min": 20,
                "qty_max": 80,
                "qty_to_order": 60,
            },
        ]
    
    def get_product_inventory(self, product_sku: str) -> Dict[str, float]:
        """
        Fetch current inventory for a product by SKU.
        
        Args:
            product_sku: Product SKU code
            
        Returns:
            Dictionary with qty_available, incoming_qty, outgoing_qty
        """
        if self.config.use_mock or not self.models:
            return self._mock_product_inventory(product_sku)
        
        try:
            # Search for product by default_code (SKU)
            product_ids = self.models.execute_kw(
                self.config.db,
                self.uid,
                self.config.password,
                "product.product",
                "search",
                [[["default_code", "=", product_sku]]],
            )
            
            if not product_ids:
                return {"qty_available": 0, "incoming_qty": 0, "outgoing_qty": 0}
            
            # Get inventory data
            product_data = self.models.execute_kw(
                self.config.db,
                self.uid,
                self.config.password,
                "product.product",
                "read",
                [product_ids],
                {"fields": ["qty_available", "incoming_qty", "outgoing_qty"]},
            )
            
            if product_data:
                return {
                    "qty_available": float(product_data[0].get("qty_available", 0)),
                    "incoming_qty": float(product_data[0].get("incoming_qty", 0)),
                    "outgoing_qty": float(product_data[0].get("outgoing_qty", 0)),
                }
        except Exception as e:
            print(f"Error fetching Odoo inventory for {product_sku}: {e}")
            return self._mock_product_inventory(product_sku)
        
        return {"qty_available": 0, "incoming_qty": 0, "outgoing_qty": 0}
    
    def get_reorder_suggestions(self) -> List[Dict]:
        """
        Get Odoo's reorder suggestions (orderpoints below minimum).
        
        Returns:
            List of dictionaries with product_id, qty_min, qty_max, qty_to_order
        """
        if self.config.use_mock or not self.models:
            return self._mock_reorder_suggestions()
        
        try:
            # Get orderpoints where qty_available < qty_min
            orderpoints = self.models.execute_kw(
                self.config.db,
                self.uid,
                self.config.password,
                "stock.warehouse.orderpoint",
                "search_read",
                [[["qty_available", "<", "qty_min"]]],
                {"fields": ["product_id", "qty_min", "qty_max", "qty_to_order"]},
            )
            return orderpoints
        except Exception as e:
            print(f"Error fetching Odoo reorder suggestions: {e}")
            return self._mock_reorder_suggestions()
    
    def sync_inventory_to_dataframe(
        self, product_features: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Sync inventory from Odoo to product features DataFrame.
        
        Args:
            product_features: DataFrame with product data including 'sku' column
            
        Returns:
            Updated DataFrame with on_hand_units, on_order_units, reserved_units
        """
        updated = product_features.copy()
        
        for idx, row in updated.iterrows():
            sku = row.get("sku", "")
            if not sku:
                continue
            
            inventory = self.get_product_inventory(sku)
            updated.at[idx, "on_hand_units"] = inventory.get("qty_available", 0)
            updated.at[idx, "on_order_units"] = inventory.get("incoming_qty", 0)
            updated.at[idx, "reserved_units"] = inventory.get("outgoing_qty", 0)
        
        return updated


