"""
Backend utilities for the Gradio demo that showcases surrogate model inference.

This module keeps model/data loading and inference logic separate from the
frontend definition in `scripts/run_gradio_demo.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Optional

import pandas as pd

from src.surrogate.features import prepare_prediction_features
from src.surrogate.model import SurrogateModel


@dataclass
class ScenarioResult:
    """Container for a single inference run."""

    product_id: str
    predictions: Dict[str, Any]
    baseline: Dict[str, Any]
    features: Dict[str, Any]
    inference_ms: float
    model_backend: str


class SurrogateDemoBackend:
    """Load the trained surrogate model and provide scenario inference helpers."""

    def __init__(
        self,
        data_dir: Path | str | None = None,
        model_dir: Path | str | None = None,
    ):
        # Go up from src/demo/backend.py -> src/demo/ -> src/ -> project root
        project_root = Path(__file__).resolve().parents[2]
        self.data_dir = Path(data_dir) if data_dir else project_root / "data" / "processed"
        self.model_dir = Path(model_dir) if model_dir else self.data_dir / "surrogate_model"
        self.raw_dir = project_root / "data" / "raw"

        self._load_assets()

    # ------------------------------------------------------------------ #
    # Loading helpers
    # ------------------------------------------------------------------ #
    def _safe_read_parquet(self, path: Path) -> pd.DataFrame:
        """Read parquet with error handling for corrupted files."""
        if not path.exists():
            return pd.DataFrame()
        try:
            return pd.read_parquet(path)
        except (OSError, Exception) as e:
            # Parquet file may be corrupted - try to regenerate
            print(f"Warning: Could not read {path}: {e}")
            print("Attempting to regenerate from raw data...")
            return self._regenerate_parquet(path)
    
    def _regenerate_parquet(self, path: Path) -> pd.DataFrame:
        """Regenerate a parquet file by running the data pipeline."""
        try:
            from src import data_loader, transformations
            from src.sim_prep import prepare_simulation_inputs
            
            print("Loading raw data and regenerating processed files...")
            raw_frames = data_loader.load_raw_frames()
            snapshot = transformations.build_planning_snapshot(raw_frames)
            sim_inputs = prepare_simulation_inputs(raw_frames)
            
            # Save the files that might be needed
            if "product_features" in str(path):
                snapshot["product_features"].to_parquet(path, index=False)
                return snapshot["product_features"]
            elif "expanded_promos" in str(path):
                sim_inputs["expanded_promos"].to_parquet(path, index=False)
                return sim_inputs["expanded_promos"]
            elif "ad_spend" in str(path):
                snapshot["ad_spend"].to_parquet(path, index=False)
                return snapshot["ad_spend"]
            
            return pd.DataFrame()
        except Exception as e:
            print(f"Error regenerating {path}: {e}")
            return pd.DataFrame()

    def _safe_read_csv(self, path: Path) -> pd.DataFrame:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()

    def _load_assets(self) -> None:
        """Load model plus supporting feature tables."""
        self.model = SurrogateModel.load(self.model_dir)

        self.product_features = self._safe_read_parquet(self.data_dir / "product_features.parquet")
        self.expanded_promos = self._safe_read_parquet(self.data_dir / "expanded_promos.parquet")
        self.ad_spend = self._safe_read_parquet(self.data_dir / "ad_spend.parquet")
        self.initial_inventory = self._safe_read_csv(self.raw_dir / "current_inventory.csv")

        if self.product_features.empty:
            raise FileNotFoundError("product_features parquet not found. Run the data pipeline first.")

        self.base_features = prepare_prediction_features(
            product_features=self.product_features,
            expanded_promos=self.expanded_promos,
            ad_spend=self.ad_spend,
            initial_inventory=self.initial_inventory if not self.initial_inventory.empty else None,
        )
        self.base_predictions = self.model.predict(self.base_features)

        # Capture the underlying estimator name for UI display
        self.model_backend = (
            type(next(iter(self.model.models.values()))).__name__
            if self.model.models
            else "UnknownModel"
        )

    # ------------------------------------------------------------------ #
    # Public helpers
    # ------------------------------------------------------------------ #
    @property
    def product_choices(self) -> list[str]:
        return self.product_features["product_id"].tolist()

    @property
    def product_labels(self) -> Dict[str, str]:
        return {
            row["product_id"]: f"{row['product_id']} — {row['name']} ({row['category']})"
            for _, row in self.product_features[["product_id", "name", "category"]].iterrows()
        }

    def default_on_hand(self, product_id: str) -> float:
        row = self.base_features.loc[self.base_features["product_id"] == product_id]
        return float(row["on_hand_start"].iloc[0]) if not row.empty else 0.0

    def run_scenario(
        self,
        product_id: str,
        discount_pct: float = 0.0,
        ad_multiplier: float = 1.0,
        on_hand_override: Optional[float] = None,
        promo_days: int = 7,
    ) -> ScenarioResult:
        """Apply user overrides and run inference."""
        if product_id not in set(self.product_features["product_id"]):
            raise ValueError(f"Unknown product_id '{product_id}'")

        features = self.base_features.copy()
        mask = features["product_id"] == product_id

        # Promo knobs
        features.loc[mask, "avg_discount"] = float(discount_pct)
        features.loc[mask, "max_discount"] = float(discount_pct)
        features.loc[mask, "total_discount"] = float(discount_pct) * promo_days
        features.loc[mask, "promo_days"] = promo_days if discount_pct > 0 else 0

        # Ad spend scaling
        if ad_multiplier and ad_multiplier != 1.0:
            features.loc[mask, ["total_ad_spend", "avg_daily_ad_spend"]] = (
                features.loc[mask, ["total_ad_spend", "avg_daily_ad_spend"]] * float(ad_multiplier)
            )

        # Inventory override
        if on_hand_override is not None:
            features.loc[mask, "on_hand_start"] = float(on_hand_override)

        # Run inference with timing
        start = perf_counter()
        predictions = self.model.predict(features)
        elapsed_ms = (perf_counter() - start) * 1000.0

        scenario_row = predictions.loc[mask].iloc[0].to_dict()
        baseline_row = self.base_predictions.loc[
            self.base_predictions["product_id"] == product_id
        ].iloc[0].to_dict()
        feature_row = features.loc[
            mask,
            [
                "avg_discount",
                "total_discount",
                "promo_days",
                "total_ad_spend",
                "avg_daily_ad_spend",
                "on_hand_start",
            ],
        ].iloc[0].to_dict()

        return ScenarioResult(
            product_id=product_id,
            predictions=scenario_row,
            baseline=baseline_row,
            features=feature_row,
            inference_ms=elapsed_ms,
            model_backend=self.model_backend,
        )


