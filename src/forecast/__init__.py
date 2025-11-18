"""
Forecasting utilities, including Orbit integration and stub model.
"""

# Try to import real integration, fallback to stub
try:
    from .orbit_integration import forecast_bundle, OrbitConfig
    __all__ = ["forecast_bundle", "OrbitConfig"]
except (ImportError, AttributeError):
    from .orbit_stub import forecast_bundle
    # Create a simple config class for compatibility
    from dataclasses import dataclass
    @dataclass
    class OrbitConfig:
        horizon_days: int = 30
        seasonality: list = None
        prediction_percentiles: list = None
        use_real_orbit: bool = False
    __all__ = ["forecast_bundle", "OrbitConfig"]


