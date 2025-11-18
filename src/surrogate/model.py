"""
Surrogate model implementation using XGBoost with GPU support.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# Try to import XGBoost, fallback to sklearn
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    xgb = None

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@dataclass
class SurrogateConfig:
    """Configuration for surrogate model training."""
    use_gpu: bool = True
    n_estimators: int = 100
    max_depth: int = 6
    learning_rate: float = 0.1
    test_size: float = 0.2
    random_state: int = 42
    target_metrics: List[str] = None  # If None, trains on all available targets


class SurrogateModel:
    """
    Surrogate model for fast simulation prediction.
    
    Uses XGBoost with GPU support if available, otherwise falls back to RandomForest.
    """
    
    def __init__(self, config: SurrogateConfig | None = None):
        self.config = config or SurrogateConfig()
        self.models: Dict[str, any] = {}
        self.feature_names: List[str] = []
        self.target_names: List[str] = []
        self.is_fitted = False
    
    def _get_model(self, target_name: str):
        """Get or create model for a target."""
        if target_name in self.models:
            return self.models[target_name]
        
        if XGBOOST_AVAILABLE and self.config.use_gpu:
            try:
                # Try GPU first
                model = xgb.XGBRegressor(
                    n_estimators=self.config.n_estimators,
                    max_depth=self.config.max_depth,
                    learning_rate=self.config.learning_rate,
                    tree_method="gpu_hist",  # GPU method
                    random_state=self.config.random_state,
                    verbosity=0,
                )
                self.models[target_name] = model
                return model
            except Exception:
                # Fallback to CPU
                print(f"Warning: GPU not available for {target_name}, using CPU")
                model = xgb.XGBRegressor(
                    n_estimators=self.config.n_estimators,
                    max_depth=self.config.max_depth,
                    learning_rate=self.config.learning_rate,
                    random_state=self.config.random_state,
                    verbosity=0,
                )
                self.models[target_name] = model
                return model
        elif XGBOOST_AVAILABLE:
            model = xgb.XGBRegressor(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                learning_rate=self.config.learning_rate,
                random_state=self.config.random_state,
                verbosity=0,
            )
            self.models[target_name] = model
            return model
        elif SKLEARN_AVAILABLE:
            model = RandomForestRegressor(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                random_state=self.config.random_state,
                n_jobs=-1,
            )
            self.models[target_name] = model
            return model
        else:
            raise ImportError("Neither XGBoost nor sklearn available. Please install xgboost or scikit-learn.")
    
    def fit(self, X: pd.DataFrame, y: pd.DataFrame) -> Dict[str, Dict]:
        """
        Train surrogate models for each target.
        
        Args:
            X: Feature DataFrame (must include product_id)
            y: Target DataFrame (must include product_id)
            
        Returns:
            Dictionary of training metrics per target
        """
        # Store feature and target names
        self.feature_names = [col for col in X.columns if col != "product_id"]
        self.target_names = [col for col in y.columns if col != "product_id"]
        
        # Filter targets if specified
        if self.config.target_metrics:
            self.target_names = [t for t in self.target_names if t in self.config.target_metrics]
        
        # Prepare feature matrix (exclude product_id)
        X_features = X[self.feature_names].values
        
        metrics = {}
        
        for target_name in self.target_names:
            if target_name not in y.columns:
                continue
            
            y_target = y[target_name].values
            
            # Split train/test
            X_train, X_test, y_train, y_test = train_test_split(
                X_features,
                y_target,
                test_size=self.config.test_size,
                random_state=self.config.random_state,
            )
            
            # Train model
            model = self._get_model(target_name)
            model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)
            
            metrics[target_name] = {
                "mae": float(mae),
                "rmse": float(rmse),
                "r2": float(r2),
                "n_train": len(X_train),
                "n_test": len(X_test),
            }
        
        self.is_fitted = True
        return metrics
    
    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Predict targets for given features.
        
        Args:
            X: Feature DataFrame (must include product_id)
            
        Returns:
            DataFrame with predictions (product_id + target columns)
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        X_features = X[self.feature_names].values
        predictions = {"product_id": X["product_id"].values}
        
        for target_name in self.target_names:
            if target_name in self.models:
                model = self.models[target_name]
                predictions[target_name] = model.predict(X_features)
        
        return pd.DataFrame(predictions)
    
    def save(self, model_dir: Path) -> None:
        """Save model to directory."""
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save models
        for target_name, model in self.models.items():
            if XGBOOST_AVAILABLE:
                model_path = model_dir / f"{target_name}.json"
                model.save_model(str(model_path))
            else:
                import pickle
                model_path = model_dir / f"{target_name}.pkl"
                with open(model_path, "wb") as f:
                    pickle.dump(model, f)
        
        # Save metadata
        metadata = {
            "feature_names": self.feature_names,
            "target_names": self.target_names,
            "is_fitted": self.is_fitted,
            "config": {
                "use_gpu": self.config.use_gpu,
                "n_estimators": self.config.n_estimators,
                "max_depth": self.config.max_depth,
                "learning_rate": self.config.learning_rate,
            },
        }
        metadata_path = model_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2))
    
    @classmethod
    def load(cls, model_dir: Path) -> "SurrogateModel":
        """Load model from directory."""
        metadata_path = model_dir / "metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata not found in {model_dir}")
        
        metadata = json.loads(metadata_path.read_text())
        config = SurrogateConfig(**metadata["config"])
        model = cls(config)
        
        model.feature_names = metadata["feature_names"]
        model.target_names = metadata["target_names"]
        model.is_fitted = metadata["is_fitted"]
        
        # Load models
        for target_name in model.target_names:
            if XGBOOST_AVAILABLE:
                model_path = model_dir / f"{target_name}.json"
                if model_path.exists():
                    loaded_model = xgb.XGBRegressor()
                    loaded_model.load_model(str(model_path))
                    model.models[target_name] = loaded_model
            else:
                import pickle
                model_path = model_dir / f"{target_name}.pkl"
                if model_path.exists():
                    with open(model_path, "rb") as f:
                        model.models[target_name] = pickle.load(f)
        
        return model


def train_surrogate_model(
    simulation_logs: pd.DataFrame,
    product_features: pd.DataFrame,
    expanded_promos: pd.DataFrame,
    ad_spend: pd.DataFrame,
    config: SurrogateConfig | None = None,
) -> tuple[SurrogateModel, Dict]:
    """
    Train surrogate model on simulation logs.
    
    Args:
        simulation_logs: Simulation results
        product_features: Product features
        expanded_promos: Promotional calendar
        ad_spend: Ad spend data
        config: Model configuration
        
    Returns:
        Tuple of (trained_model, training_metrics)
    """
    from .features import prepare_training_features
    
    # Prepare features and targets
    X, y = prepare_training_features(
        simulation_logs,
        product_features,
        expanded_promos,
        ad_spend,
    )
    
    # Train model
    model = SurrogateModel(config)
    metrics = model.fit(X, y)
    
    return model, metrics

