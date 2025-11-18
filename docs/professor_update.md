# Milestone 1 Progress Update — Sell-Through Co-Pilot

## Executive Summary

We have successfully implemented a **reproducible data collection and simulation pipeline** that connects demand forecasting, promotional response modeling, and inventory re-stocking logic. This foundation enables us to generate labeled training data for the future AI surrogate model.

---

## What We've Built

### 1. **Data Collection Pipeline** ✅

**Raw Data Sources:**
- Product master data (4 SKUs across apparel, electronics, accessories)
- Historical sales by product, channel, and date
- Returns data with time-to-return metrics
- Supplier lead-time statistics
- Promotion calendar with discount schedules
- Advertising spend by channel and date
- Current inventory positions

**Pipeline Components:**
- **Validation Layer**: Schema checks, data integrity guards, negative-value detection
- **Transformation Layer**: Daily demand aggregation, return rate calculations, safety stock computation
- **Feature Engineering**: Product feature tables combining master data, demand stats, returns, and lead times

**Outputs:**
- `daily_demand.parquet`: Time-series demand by product/channel
- `product_features.parquet`: Enriched product attributes for simulation
- `expanded_promos.parquet`: Day-level promotional schedule
- `simulation_schedule.parquet`: 30-day forward planning table

---

### 2. **Traditional Model Facsimiles** ✅

**Uber Orbit Stub** (`src/forecast/orbit_stub.py`):
- Exponential smoothing demand forecasting
- Produces baseline forecasts with uncertainty intervals
- Compatible with Orbit's daily forecast interface
- Generates forecasts for all products in the catalog

**Meta Robyn Stub** (`src/promo/robyn_stub.py`):
- Promotional discount lift modeling
- Advertising spend carryover effects
- Generates lift multipliers per product/date
- Mirrors Robyn's response curve outputs

**Odoo/ERPNext Inventory Simulator** (`src/simulations/inventory_engine.py`):
- Min-max reorder policy implementation
- Lead-time uncertainty handling
- Case-pack rounding and MOQ constraints
- Day-by-day inventory play-out with backlog tracking

---

### 3. **Slow Simulation Engine** ✅

**What It Does:**
- Combines Orbit forecasts + Robyn lift factors
- Applies ERP-style reorder rules
- Simulates daily inventory positions, demand realization, lost sales, and purchase orders
- Logs all outcomes for downstream surrogate training

**Simulation Logs:**
- `sim_log.parquet`: Day-level records with:
  - On-hand inventory (start/end)
  - Projected vs. realized demand
  - Lost sales and backlog
  - Purchase order quantities
  - Safety stock levels

**Summary Metrics:**
- Total projected demand per SKU
- Total realized sales
- Lost sales (stock-outs)
- Total orders placed

**Example Output (21-day simulation):**
- 4 products simulated
- 84 day-product records logged
- Captures run-out scenarios, overstock situations, and reorder triggers

---

## Technical Architecture

```
Raw CSVs → Data Pipeline → Processed Tables
                              ↓
                    Orbit Stub (forecasts)
                              ↓
                    Robyn Stub (lift factors)
                              ↓
                    Inventory Simulator
                              ↓
                    Simulation Logs (training data)
```

---

## Key Achievements

1. **Reproducible Data Flow**: Single command (`scripts/run_data_pipeline.py`) validates, transforms, and outputs canonical tables
2. **Traditional Model Integration**: Python facsimiles of Orbit and Robyn produce realistic forecasts and lift factors
3. **Inventory Simulation**: Odoo/ERPNext-style reorder logic generates day-by-day inventory outcomes
4. **Training Data Generation**: Slow simulations produce labeled examples (demand, inventory, orders) for future surrogate model training
5. **Scalable Foundation**: Pipeline designed to swap synthetic data for live ERP extracts without changing downstream components

---

## Deliverables

- ✅ Complete Python package (`src/`) with data loading, validation, transformations, and simulation
- ✅ CLI scripts for pipeline execution and slow simulation runs
- ✅ Sample datasets for 4 representative products
- ✅ Processed Parquet files ready for Orbit/Robyn integration
- ✅ First logged simulation runs (84 records across 4 SKUs)
- ✅ Documentation (README, milestone report, demo script)
- ✅ GitHub repository: `https://github.com/RockFZ/Sell-Through-Co-Pilot`

---

## Next Steps (Milestone 2)

1. Replace Python stubs with actual Orbit and Robyn runs
2. Expand simulation to 5+ products
3. Generate larger simulation dataset for surrogate training
4. Begin GPU-based surrogate model development (XGBoost)

---

## Demo Capabilities

We can demonstrate:
- Running the data pipeline end-to-end
- Generating forecasts and lift factors
- Executing slow inventory simulations
- Inspecting simulation logs and metrics
- Showing how the pipeline scales to additional products

---

## Questions for Discussion

1. **Data Volume**: Should we expand to more products/SKUs for the surrogate training dataset?
2. **Model Fidelity**: Are the Orbit/Robyn stubs sufficient for now, or should we prioritize real model integration?
3. **Simulation Scenarios**: Which scenarios (normal week, big promo, influencer spike) should we prioritize?
4. **Evaluation Metrics**: What KPIs should we track in the simulation logs for surrogate training?

---

**Repository**: https://github.com/RockFZ/Sell-Through-Co-Pilot  
**Contact**: Ready to demo the pipeline and discuss next steps.


