"""
Surrogate model for fast simulation prediction.
"""

from .model import SurrogateModel, SurrogateConfig, train_surrogate_model
from .features import prepare_training_features, prepare_prediction_features

__all__ = [
    "SurrogateModel",
    "SurrogateConfig",
    "train_surrogate_model",
    "prepare_training_features",
    "prepare_prediction_features",
]

