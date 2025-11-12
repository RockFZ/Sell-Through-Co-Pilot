## Milestone 1 — Data Plumbing Summary

### Objectives
- Consolidate operational inputs (products, demand, returns, lead times, promotions, ads, inventory) into a coherent schema.
- Provide validation and transformation utilities that normalize raw sources.
- Emit simulation-ready tables for the slow inventory play-out and future surrogate training.

### Deliverables
- Synthetic raw datasets for 4 representative products across apparel, electronics, and accessories.
- Python package (`src/`) containing:
  - `config.py` — path helpers.
  - `data_models.py` — typed records for each dataset.
  - `validation.py` — structural checks and negative-value guards.
  - `data_loader.py` — bulk CSV ingestion with automatic validation.
  - `transformations.py` — feature engineering (daily demand, returns, safety stock).
  - `sim_prep.py` — promo expansion and 30-day simulation schedule builder.
- `forecast/orbit_stub.py` — exponential smoothing Orbit facsimile with uncertainty bounds.
- `promo/robyn_stub.py` — discount + ad carryover lift table generator.
- `simulations/inventory_engine.py` — min–max reorder simulation inspired by Odoo/ERPNext.
- CLI script `scripts/run_data_pipeline.py` to run the full pipeline and persist processed Parquet files.
- CLI script `scripts/run_slow_simulation.py` that chains the facsimiles and logs “slow” simulations.
- `requirements.txt` and `README.md` for setup guidance.

### Processed outputs
- `daily_demand.parquet`: Aggregated demand by day-product-channel.
- `product_features.parquet`: Merge of product master, demand stats, returns, lead-time metrics, and inventory.
- `expanded_promos.parquet`: Day-level promo schedule with discount factors.
- `simulation_schedule.parquet`: 30-day forward plan with demand baseline, promo placeholders, and operational constraints.
- `slow_simulations/sim_log.parquet`: Day-level inventory positions, demand realization, lost sales, and orders.
- `slow_simulations/sim_summary.json`: Roll-up metrics per SKU.
- Optional summary JSON from pipeline execution.

### Validation coverage
- Column order + presence for every raw CSV.
- Product ID integrity across files.
- Guards against negative sales, returns, and ad spend entries.
- Discount bounds (0–100%).

### Usage notes & next steps
- The simulation schedule primes the “slow engine” with baseline forecasts, safety stock hints, and promo windows. Orbit/Robyn facsimiles generate demand forecasts and lift factors that feed the Odoo/ERPNext-style min–max simulator.
- Future milestones should replace synthetic data with live extracts (Odoo/ERPNext APIs) using the same schema, keeping downstream components unchanged.

