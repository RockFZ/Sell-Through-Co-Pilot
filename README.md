# Sell-Through Co-Pilot — Milestone 1

This repository contains the Milestone 1 deliverables for the **Sell-Through Co-Pilot** project. The focus of this milestone is on **data plumbing**—collecting raw operational inputs, validating schemas, and producing canonical tables that downstream forecasting, marketing mix, and simulation workflows can consume.

## Repo layout

- `data/raw/`: Synthetic source files for products, sales history, lead times, returns, promotions, ads, and inventory.
- `data/processed/`: Generated Parquet tables after running the pipeline.
- `src/`: Python package with config, validation, transformations, and simulation prep utilities.
- `scripts/`: CLI entry points. `run_data_pipeline.py` executes the end-to-end data plumbing workflow.
- `docs/`: Documentation and milestone notes (see `docs/milestone1_report.md`).

## Quick start

Create a virtual environment (recommended) and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the data pipeline, which will validate raw inputs, create processed artifacts, and emit a JSON summary:

```bash
python scripts/run_data_pipeline.py --output-summary data/processed/summary.json
```

Key outputs:

- `data/processed/daily_demand.parquet`
- `data/processed/product_features.parquet`
- `data/processed/expanded_promos.parquet`
- `data/processed/simulation_schedule.parquet`
- `data/processed/summary.json`

Run the slow simulation to generate logged inventory outcomes using the Orbit/Robyn facsimiles and min-max reorder rules:

```bash
python scripts/run_slow_simulation.py --horizon-days 21
```

Simulation artifacts:

- `data/processed/slow_simulations/sim_log.parquet`
- `data/processed/slow_simulations/sim_summary.json`

## Next steps

Milestone 2 (forecasting + promo lift prototypes) will consume the processed tables prepared here. The simulation schedule already includes baseline demand, promotion placeholders, lead-time statistics, and safety-stock hints to seed the slow engine and surrogate training efforts.

