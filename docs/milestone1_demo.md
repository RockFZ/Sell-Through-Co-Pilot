## Milestone 1 Demo Guide

This walkthrough shows how to reproduce the Sell-Through Co-Pilot Milestone 1 “data plumbing” deliverable with the Python facsimiles for Orbit, Robyn, and ERP-style replenishment.

### 1. Environment setup

```bash
cd "/Users/zhufucheng/Desktop/EE542/Final Project/Milestone1"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Generate processed data tables

```bash
python scripts/run_data_pipeline.py --output-summary data/processed/summary.json
```

What to show on screen:
- Terminal output confirming successful run.
- Open `data/processed/summary.json` to highlight the row counts and columns for each canonical table.

### 3. Run the slow simulation

```bash
python scripts/run_slow_simulation.py --horizon-days 21
```

What to show:
- Terminal summary of projected vs realized demand, lost sales, and total orders per SKU.
- Open `data/processed/slow_simulations/sim_log.parquet` using a Parquet viewer or with a quick Python snippet:

```bash
python - <<'PY'
import pandas as pd
print(pd.read_parquet("data/processed/slow_simulations/sim_log.parquet").head())
PY
```

Emphasize that the log contains day-level inventory states and orders, which become training labels for the GPU surrogate.

### 4. Inspect the facsimile components (optional b-roll)

- `src/forecast/orbit_stub.py`: show the exponential smoothing forecast bundle.
- `src/promo/robyn_stub.py`: highlight how discount and ad spend lift factors are combined.
- `src/simulations/inventory_engine.py`: point out min–max reorder logic and lead-time handling.

### 5. Close with deliverable recap

Call out:
- Raw → processed pipeline
- Promo/ad lift table
- Slow simulation outputs
- Alignment with milestone plan (data plumbing + first logged simulation)

---

## Extended Video Script (2–3 minutes)

**Scene 1 – Opening Context (0:00–0:20)**  
Visual: Presenter on camera or title card with project branding.  
Narration: “Welcome to the Sell-Through Co-Pilot Milestone 1 demo. Our focus in this phase was data plumbing—turning raw sales, promo, and inventory feeds into a reusable foundation for the forecasting and restocking co-pilot.”

**Scene 2 – Problem & Architecture Snapshot (0:20–0:45)**  
Visual: Diagram slide showing the pipeline (Raw Inputs → Validated Tables → Orbit/Robyn Facsimiles → Inventory Simulator → Outputs).  
Narration: “Retail teams juggle demand forecasts, promotions, and replenishment in separate silos. We need a single flow that connects them. Here’s the architecture we implemented: canonical tables at the core, Orbit-style forecasts, Robyn-style lift, and ERP-style reorder logic feeding a slow simulator.”

**Scene 3 – Environment Setup & Data Pipeline (0:45–1:15)**  
Visual: Terminal running virtual environment activation and `python scripts/run_data_pipeline.py`.  
Narration: “Let’s run the pipeline. After installing dependencies we execute `run_data_pipeline.py`. It validates schemas, catches negative values, and produces Parquet artifacts under `data/processed/`. The JSON summary lists every table—daily demand, product features, promotions, and the initial simulation schedule.”
Visual follow-up: Open `data/processed/summary.json` in editor, scroll to highlight columns.

**Scene 4 – Forecast & Promo Facsimiles (1:15–1:55)**  
Visual: Split-screen or sequential shots of `src/forecast/orbit_stub.py` and `src/promo/robyn_stub.py`.  
Narration: “To iterate quickly we emulated Uber Orbit with an exponential smoothing forecaster that outputs baseline demand plus confidence bands for each SKU. For marketing effects we mimic Meta Robyn—discount depth boosts and decayed ad spend turn into lift multipliers. These stubs match the interfaces of the real tools, so we can swap them later without refactoring.”  
On-screen callouts: highlight `OrbitStubConfig`, `forecast_bundle`, `promo_discount_weight`, and `ad_decay_half_life`.

**Scene 5 – Min–Max Inventory Simulation (1:55–2:35)**  
Visual: Show `src/simulations/inventory_engine.py` near the reorder logic, then run `python scripts/run_slow_simulation.py --horizon-days 21`.  
Narration: “Those feeds drive an Odoo/ERPNext-style replenishment simulator. We track on-hand stock, inbound orders, and backlogs. When inventory dips below the min level, we round orders to case packs and respect supplier lead times. Running the script logs 21 days of behavior for four SKUs.”  
Visual follow-up: Open `data/processed/slow_simulations/sim_summary.json`, highlight projected vs realized demand and lost sales numbers.

**Scene 6 – Inspecting the Simulation Log (2:35–2:50)**  
Visual: Quick Python snippet showing `pd.read_parquet(...).head()`.  
Narration: “The detailed log captures daily inventory states—perfect training data for our GPU surrogate and upcoming Ray search. It’s also ready for dashboards and KPI reviews.”

**Scene 7 – Wrap-up & Next Steps (2:50–3:00)**  
Visual: Presenter back on screen or closing slide with bullets: “Swap in real Orbit/Robyn”, “Add more SKUs”, “Train surrogate”, “Ray trust-but-verify”.  
Narration: “Milestone 1 delivers the reproducible data flow plus our first slow simulations. Next we plug in full Orbit/Robyn runs, expand the catalog, and start training the surrogate model before scaling search with Ray. Thanks for watching.”

---

## Visual Shot List

| Scene | Duration | Visuals | Overlays / Callouts |
|-------|----------|---------|----------------------|
| 1 — Intro | ~10s | Presenter webcam or title card with project name on slide | Text overlay: “Milestone 1 – Data Plumbing” |
| 2 — Pipeline Run | ~20s | Screen capture of terminal executing `python scripts/run_data_pipeline.py` | Highlight the “Data pipeline executed successfully” message; sidebar pop-up listing produced Parquet files |
| 3 — Orbit Stub | ~10s | VS Code window with `src/forecast/orbit_stub.py`; cursor hover on `forecast_bundle` | Annotation arrow pointing to `OrbitStubConfig`; text: “Orbit facsimile” |
| 3b — Robyn Stub | ~5s | Switch tab to `src/promo/robyn_stub.py`; scroll through lift calculation | Callout bubble: “Promo + ad lift factors” |
| 4 — Slow Simulation | ~25s | Terminal running `python scripts/run_slow_simulation.py`; after run, open `sim_summary.json` in editor | Highlight projected vs realized demand numbers; overlay “First slow simulation log” |
| 4b — Log Preview | ~10s | Quick Python REPL/Notebook showing `head()` of `sim_log.parquet` | Text overlay: “Per-day inventory states + orders” |
| 5 — Architecture Recap | ~10s | Slide or Miro-style diagram showing data flow: Raw Inputs → Pipeline → Orbit/Robyn → Inventory Sim → Surrogate | Animated arrows to emphasize flow |
| 6 — Next Steps & Outro | ~10s | Presenter back on screen or closing slide with bullet list “Next: Forecasting / Surrogate / Ray Search” | Fade in logo or project name and “Thanks for watching” |

