"""
Project-level configuration utilities for Sell-Through Co-Pilot.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataPaths:
    """Canonical locations for raw and processed datasets."""

    root: Path

    @property
    def raw_dir(self) -> Path:
        return self.root / "data" / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.root / "data" / "processed"

    @property
    def schemas_dir(self) -> Path:
        return self.root / "docs" / "schemas"


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATHS = DataPaths(root=PROJECT_ROOT)


