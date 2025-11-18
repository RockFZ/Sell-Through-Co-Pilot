"""
Promotion and advertising response utilities, including Robyn integration.
"""

# Try to import real integration, fallback to stub
try:
    from .robyn_integration import build_lift_table, RobynConfig
    __all__ = ["build_lift_table", "RobynConfig"]
except (ImportError, AttributeError):
    from .robyn_stub import build_lift_table
    # Create a simple config class for compatibility
    from dataclasses import dataclass
    @dataclass
    class RobynConfig:
        promo_discount_weight: float = 1.6
        ad_spend_weight: float = 0.0002
        ad_decay_half_life: int = 3
        ad_saturation_threshold: float = 500.0
        use_real_robyn: bool = False
    __all__ = ["build_lift_table", "RobynConfig"]

