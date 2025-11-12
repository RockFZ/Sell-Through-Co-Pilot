# Slide: Milestone 1 Data Plumbing Pipeline

## Title
**Sell-Through Co-Pilot – Milestone 1 Pipeline Overview**

## Visual Diagram
```
┌────────────┐    ┌────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────────┐
│ Raw Inputs │ -> │ Validation &   │ -> │ Forecast Facsimile   │ -> │ Inventory Simulator  │ -> │ Logged Slow Simulations │
│ products   │    │ Canonical      │    │ (Orbit Stub)         │    │ (Min–Max Reorder)    │    │ sim_log.parquet,        │
│ sales      │    │ Tables         │    │ + Promo/Ad Lift      │    │ with lead times      │    │ sim_summary.json        │
│ promos     │    │ daily_demand   │    │ (Robyn Stub)         │    │ and backlog tracking │    │                         │
│ ads spend  │    │ product_features│   │ total_lift table     │    │ orders, stock levels │    │ training-ready dataset  │
│ inventory  │    │ simulation_schedule │ horizon forecasts   │    │ KPI capture          │    │ for surrogate model      │
└────────────┘    └────────────────┘    └─────────────────────┘    └─────────────────────┘    └─────────────────────────┘
```

## Slide Notes (talk track)
- **Raw Inputs**: Synthetic extracts for 4 SKUs covering products, sales, returns, promotions, ad spend, and inventory snapshots.
- **Validation & Canonical Tables**: `run_data_pipeline.py` enforces schema checks, then emits `daily_demand`, `product_features`, `expanded_promos`, and `simulation_schedule`.
- **Forecast & Promo Facsimiles**: Orbit-style exponential smoothing generates 30-day demand forecasts; Robyn-style lift table combines discount depth with decayed ad spend.
- **Inventory Simulator**: Odoo/ERPNext-inspired min–max logic respects lead times, case packs, and backlog caps while logging realized demand and orders.
- **Logged Slow Simulations**: Outputs stored under `data/processed/slow_simulations/` become labeled training data for the GPU surrogate and Ray scaling in later milestones.

## Suggested Slide Layout
- Left column: Diagram above.
- Right column: Bullet list summarizing key components and tools (Orbit Stub, Robyn Stub, Min–Max engine, Parquet outputs).
- Footer: “Milestone 1 — Reproducible data flow powering Sell-Through Co-Pilot”.


