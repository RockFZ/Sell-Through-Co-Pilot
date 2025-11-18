"""
ERPNext ERP integration client.

Supports both real ERPNext REST API and mock mode for development.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import json

import pandas as pd

# Try to import requests, fallback to mock
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


@dataclass
class ERPNextConfig:
    """Configuration for ERPNext connection."""
    url: str = "http://localhost:8000"
    api_key: str = "your_api_key"
    api_secret: str = "your_api_secret"
    use_mock: bool = False  # Set to True to use mock data


class ERPNextClient:
    """
    Client for interacting with ERPNext ERP system.
    
    Supports both real API calls and mock mode for development/testing.
    """
    
    def __init__(self, config: ERPNextConfig | None = None):
        self.config = config or ERPNextConfig()
        self.session = None
        
        if not self.config.use_mock and REQUESTS_AVAILABLE:
            try:
                self.session = requests.Session()
                self.session.headers.update({
                    "Authorization": f"token {self.config.api_key}:{self.config.api_secret}",
                    "Content-Type": "application/json",
                })
                # Test connection
                response = self.session.get(f"{self.config.url}/api/method/frappe.auth.get_logged_user")
                if response.status_code != 200:
                    print("Warning: ERPNext connection failed, using mock mode")
                    self.config.use_mock = True
            except Exception as e:
                print(f"Warning: Could not connect to ERPNext, using mock mode: {e}")
                self.config.use_mock = True
    
    def _mock_item_stock(self, item_code: str, warehouse: str = None) -> Dict:
        """Mock stock data for development."""
        mock_data = {
            "SKU-002": {"actual_qty": 60, "reserved_qty": 3, "ordered_qty": 0},
            "SKU-004": {"actual_qty": 35, "reserved_qty": 1, "ordered_qty": 15},
        }
        return mock_data.get(item_code, {"actual_qty": 50, "reserved_qty": 0, "ordered_qty": 0})
    
    def _mock_reorder_suggestions(self) -> List[Dict]:
        """Mock reorder suggestions for development."""
        return [
            {
                "item_code": "SKU-002",
                "reorder_level": 30,
                "reorder_qty": 60,
            },
            {
                "item_code": "SKU-004",
                "reorder_level": 25,
                "reorder_qty": 50,
            },
        ]
    
    def get_item_stock(
        self, item_code: str, warehouse: str | None = None
    ) -> Dict[str, float]:
        """
        Fetch current stock for an item.
        
        Args:
            item_code: Item code (SKU)
            warehouse: Optional warehouse name
            
        Returns:
            Dictionary with actual_qty, reserved_qty, ordered_qty
        """
        if self.config.use_mock or not self.session:
            return self._mock_item_stock(item_code, warehouse)
        
        try:
            params = {"item_code": item_code}
            if warehouse:
                params["warehouse"] = warehouse
            
            response = self.session.get(
                f"{self.config.url}/api/resource/Bin",
                params=params,
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    bin_data = data["data"][0]
                    return {
                        "actual_qty": float(bin_data.get("actual_qty", 0)),
                        "reserved_qty": float(bin_data.get("reserved_qty", 0)),
                        "ordered_qty": float(bin_data.get("ordered_qty", 0)),
                    }
        except Exception as e:
            print(f"Error fetching ERPNext stock for {item_code}: {e}")
            return self._mock_item_stock(item_code, warehouse)
        
        return {"actual_qty": 0, "reserved_qty": 0, "ordered_qty": 0}
    
    def get_reorder_suggestions(self) -> List[Dict]:
        """
        Get ERPNext's reorder suggestions (Material Requests).
        
        Returns:
            List of dictionaries with item_code, reorder_level, reorder_qty
        """
        if self.config.use_mock or not self.session:
            return self._mock_reorder_suggestions()
        
        try:
            filters = json.dumps([["docstatus", "=", 0]])  # Draft Material Requests
            response = self.session.get(
                f"{self.config.url}/api/resource/Material Request",
                params={"filters": filters},
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
        except Exception as e:
            print(f"Error fetching ERPNext reorder suggestions: {e}")
            return self._mock_reorder_suggestions()
        
        return []
    
    def sync_inventory_to_dataframe(
        self, product_features: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Sync inventory from ERPNext to product features DataFrame.
        
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
            
            stock = self.get_item_stock(sku)
            updated.at[idx, "on_hand_units"] = stock.get("actual_qty", 0)
            updated.at[idx, "on_order_units"] = stock.get("ordered_qty", 0)
            updated.at[idx, "reserved_units"] = stock.get("reserved_qty", 0)
        
        return updated


