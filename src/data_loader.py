"""
Data loading utilities for Sell-Through Co-Pilot.
"""

from __future__ import annotations

from typing import Dict

import pandas as pd

from . import config, validation

DATE_COLUMNS = {
    "sales_history": ["date"],
    "returns": ["date"],
    "promo_calendar": ["start_date", "end_date"],
    "ad_spend": ["date"],
}


def _read_csv(path: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=parse_dates)


def load_raw_frames() -> Dict[str, pd.DataFrame]:
    """
    Load all raw dataframes from disk, performing basic validation checks.
    """

    paths = validation.EXPECTED_FILES
    frames: Dict[str, pd.DataFrame] = {}
    for name, cfg in paths.items():
        parse_dates = DATE_COLUMNS.get(name, None)
        frames[name] = _read_csv(cfg["path"], parse_dates=parse_dates)

    validation.run_basic_validations(frames)
    return frames


def write_processed_frame(df: pd.DataFrame, filename: str) -> None:
    """
    Persist a processed dataframe into the processed directory.
    """

    output_path = config.DATA_PATHS.processed_dir / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)


