# Professor Meeting — Quick Reference Slides

---

## Slide 1: Project Overview

**Sell-Through Co-Pilot**
- Goal: Plan re-stocking, pricing, and promotions together using AI surrogate models
- Approach: Collect data from traditional models → Train AI → Scale across nodes
- Status: **Milestone 1 Complete** — Data collection pipeline operational

---

## Slide 2: Data Collection Pipeline (What We Built)

```
┌─────────────┐
│  Raw CSVs   │  Products, Sales, Returns, Lead Times, Promos, Ads
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Data Pipeline   │  Validation → Transformation → Feature Engineering
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Processed Data  │  daily_demand, product_features, expanded_promos
└─────────────────┘
```

**Key Outputs:**
- Validated, normalized datasets
- Enriched product features
- Simulation-ready tables

---

## Slide 3: Traditional Model Integration

**Three Components:**

1. **Orbit Stub** → Demand forecasting with uncertainty
2. **Robyn Stub** → Promo/ad lift multipliers  
3. **Inventory Simulator** → ERP-style reorder logic

**Result:** Slow but accurate simulations that generate training data

---

## Slide 4: Simulation Engine

**What It Does:**
- Combines forecasts + lift factors
- Simulates day-by-day inventory
- Logs: demand, stock levels, orders, lost sales

**Output:** `sim_log.parquet` with 84+ records ready for AI training

---

## Slide 5: Key Achievements

✅ **Reproducible pipeline** — Single command execution  
✅ **Traditional models integrated** — Orbit/Robyn/ERP facsimiles  
✅ **Training data generated** — First simulation logs complete  
✅ **Scalable foundation** — Ready for real ERP data swap  
✅ **GitHub repository** — Code shared with team

---

## Slide 6: Demo (Live)

**Show:**
1. Run data pipeline: `python scripts/run_data_pipeline.py`
2. Execute simulation: `python scripts/run_slow_simulation.py`
3. Inspect outputs: Parquet files and summary metrics

---

## Slide 7: Next Steps

**Milestone 2:**
- Replace stubs with real Orbit/Robyn
- Expand to 5+ products
- Generate larger training dataset
- Begin GPU surrogate development

---

## Talking Points

**Emphasize:**
- "We've built a complete data collection pipeline that connects traditional models"
- "The slow simulation engine generates labeled training data for our AI surrogate"
- "Everything is reproducible and ready to scale"
- "We can swap synthetic data for real ERP extracts without changing downstream code"

**Be Ready to:**
- Show the code structure (`src/` package)
- Run the pipeline live
- Explain how simulation logs feed the surrogate model
- Discuss scaling strategy (Ray/Dask for parallel search)


