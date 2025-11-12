#!/usr/bin/env python3
"""
Run the Sell-Through Co-Pilot data plumbing pipeline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import src.config as config  # pylint: disable=wrong-import-position
from src import data_loader, sim_prep, transformations  # pylint: disable=wrong-import-position


OUTPUT_FILES = {
    "daily_demand": "daily_demand.parquet",
    "product_features": "product_features.parquet",
    "expanded_promos": "expanded_promos.parquet",
    "simulation_schedule": "simulation_schedule.parquet",
}


def write_bundle(frames: Dict[str, pd.DataFrame]) -> None:
    for name, filename in OUTPUT_FILES.items():
        if name not in frames:
            continue
        data_loader.write_processed_frame(frames[name], filename)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-summary",
        type=Path,
        default=None,
        help="Optional path to write a JSON summary of processed datasets.",
    )
    args = parser.parse_args()

    raw_frames = data_loader.load_raw_frames()
    snapshot = transformations.build_planning_snapshot(raw_frames)
    sim_inputs = sim_prep.prepare_simulation_inputs(raw_frames)

    bundle = {
        "daily_demand": snapshot["daily_demand"],
        "product_features": snapshot["product_features"],
        "expanded_promos": sim_inputs["expanded_promos"],
        "simulation_schedule": sim_inputs["simulation_schedule"],
    }

    write_bundle(bundle)

    summary = {
        name: {
            "rows": len(df),
            "columns": list(df.columns),
        }
        for name, df in bundle.items()
    }

    if args.output_summary:
        args.output_summary.parent.mkdir(parents=True, exist_ok=True)
        args.output_summary.write_text(json.dumps(summary, indent=2))

    print("Data pipeline executed successfully.")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

