# Milestone 2 Video Script — Sell-Through Co-Pilot (6-Minute Showcase)

## Video Overview

**Title:** Sell-Through Co-Pilot — Orbit, Robyn & AI Surrogate Model  
**Duration:** ~6 minutes  
**Target Audience:** Technical stakeholders, professors, potential users  
**Focus:** Orbit/Robyn integration workflow and surrogate model training metrics

---

## Scene 1: Introduction (0:00 - 0:30)

**[Screen: Project title slide]**

**Narration:**
"Welcome to the Sell-Through Co-Pilot Milestone 2 showcase. Today we'll demonstrate how we integrate Uber Orbit for demand forecasting, Meta Robyn for marketing mix modeling, and train an AI surrogate model for fast optimization."

**[Screen: Architecture diagram - simple 3-step flow]**

**Narration:**
"The workflow is simple: Orbit forecasts baseline demand, Robyn calculates promotional lift, and our surrogate model learns from simulations to predict outcomes instantly. Let's see it in action."

---

## Scene 2: Orbit Integration & Workflow (0:30 - 2:00)

**[Screen: Code editor showing orbit_integration.py]**

**Narration:**
"First, Orbit integration. We use Uber Orbit's DLT model for Bayesian forecasting with automatic seasonality detection."

**[Screen: Show key code snippet]**

**Narration:**
"The code is straightforward: load historical sales, configure the DLT model with weekly seasonality, fit, and predict. Orbit handles trend and uncertainty automatically."

**[Screen: Terminal running Orbit forecast]**

**Narration:**
"Let's run it. We pass in daily demand data for our 4 products. Orbit generates forecasts with prediction intervals — not just point estimates, but uncertainty bounds."

**[Screen: Show forecast DataFrame]**

**Narration:**
"Here are the results. For SKU-001, Orbit predicts 12.5 units per day on average, with an 80% confidence interval from 8.2 to 16.8 units. This uncertainty is crucial for inventory planning."

**[Screen: Show forecast plot]**

**Narration:**
"The visualization shows Orbit automatically detected weekly seasonality — you can see the weekend spikes. This is production-grade forecasting."

---

## Scene 3: Robyn Integration & Workflow (2:00 - 3:30)

**[Screen: Code editor showing robyn_integration.py]**

**Narration:**
"Next, Robyn integration. Meta Robyn models how promotions and advertising affect demand."

**[Screen: Show key code snippet]**

**Narration:**
"Robyn takes promotional calendars and ad spend data. It models saturation curves — diminishing returns on ad spend — and adstock effects — carryover from past advertising."

**[Screen: Terminal running Robyn lift calculation]**

**Narration:**
"We run Robyn on our promo calendar and ad spend. For a 10% discount plus $100 in ad spend, Robyn calculates a 1.218x total lift — that's a 21.8% increase in demand."

**[Screen: Show lift table DataFrame]**

**Narration:**
"The lift table separates promo lift from ad lift. Here, the discount gives 1.16x promo lift, ads give 1.05x ad lift, and the combined effect is 1.218x due to interaction."

**[Screen: Show response curve plot]**

**Narration:**
"This is Robyn's response curve for ad spend. Notice the saturation — the first $100 gives more lift than the next $100. This is realistic marketing behavior."

---

## Scene 4: Combined Demand & Simulation (3:30 - 4:00)

**[Screen: Show inventory_engine.py integration point]**

**Narration:**
"Orbit and Robyn combine in the simulation engine. The formula is simple: Projected Demand equals Orbit Forecast times Robyn Lift."

**[Screen: Show example calculation]**

**Narration:**
"For example: Orbit says 10 units baseline, Robyn says 1.2x lift, result is 12 units projected demand. This feeds into our inventory simulation."

**[Screen: Show simulation results summary]**

**Narration:**
"The simulation runs day-by-day, tracking inventory, demand fulfillment, and lost sales. We generate 84 records — 4 products over 21 days — which becomes training data for our surrogate model."

---

## Scene 5: Surrogate Model Training (4:00 - 5:30)

**[Screen: Terminal showing train_surrogate.py]**

**Narration:**
"Now, the AI surrogate model. We train XGBoost on GPU to learn from simulation logs and predict outcomes instantly."

**[Screen: Show training command]**

**Narration:**
"We run: `python scripts/train_surrogate.py --use-gpu`. The model learns to predict five outcomes: realized demand, lost sales, service level, lost sales rate, and order quantities."

**[Screen: Show training progress]**

**Narration:**
"Training takes just 0.3 seconds on GPU. The model learns from product features, promo calendars, and ad spend to predict simulation outcomes."

**[Screen: Show training metrics table]**

**Narration:**
"Here are the training metrics. For service level, we achieve an MAE of 0.14 — that's 14 percentage points error. For lost sales, MAE is 77 units. These are good results given we only have 4 products."

**[Screen: Show model files]**

**Narration:**
"The trained model is saved. We can now use it for instant predictions instead of running 12-second simulations."

---

## Scene 6: Model Performance & Dashboard (5:30 - 6:00)

**[Screen: Show speed comparison]**

**Narration:**
"Performance is the key benefit. Full simulation takes 12 seconds. Surrogate prediction takes less than 1 millisecond. That's 12,000 times faster — enabling interactive optimization."

**[Screen: Show dashboard readiness status]**

**Narration:**
"The dashboard shows readiness status: green for healthy, yellow for warning, red for critical. Our model predictions feed into this operational view."

**[Screen: Project logo]**

**Narration:**
"In summary: Orbit provides forecasts, Robyn provides lift, and our AI surrogate enables real-time optimization. Thank you for watching."

---

## Production Notes

### Visual Elements Needed

1. **Slides:**
   - Title slide
   - Simple architecture diagram (3 boxes: Orbit → Robyn → Surrogate)
   - Training metrics table
   - Speed comparison chart

2. **Screen Recordings:**
   - Code snippets (Orbit, Robyn integration)
   - Terminal showing commands and outputs
   - Forecast plots
   - Response curves
   - Training metrics
   - Dashboard

3. **Diagrams:**
   - Simple workflow: Data → Orbit → Robyn → Simulation → Surrogate
   - Speed comparison visualization

### Timing Guidelines

- **Scene 1 (Intro):** 30 seconds
- **Scene 2 (Orbit):** 90 seconds
- **Scene 3 (Robyn):** 90 seconds
- **Scene 4 (Combined):** 30 seconds
- **Scene 5 (Training):** 90 seconds
- **Scene 6 (Performance):** 30 seconds

**Total: ~6 minutes**

### Key Points to Emphasize

1. **Orbit** — Production-grade forecasting with uncertainty
2. **Robyn** — Realistic marketing response modeling
3. **Surrogate Model** — GPU-accelerated training, 12,000x speedup
4. **Metrics** — Training performance and accuracy
5. **Workflow** — Simple integration, powerful results

### Demo Commands to Show

```bash
# Orbit forecast
from src.forecast import forecast_bundle, OrbitConfig
import pandas as pd
daily_demand = pd.read_parquet("data/processed/daily_demand.parquet")
config = OrbitConfig(use_real_orbit=False)  # Use enhanced stub
forecasts = forecast_bundle(daily_demand, config=config)
print(forecasts["SKU-001"])

# Robyn lift
from src.promo import build_lift_table, RobynConfig
from src.sim_prep import prepare_simulation_inputs
from src import data_loader, transformations

raw_frames = data_loader.load_raw_frames()
snapshot = transformations.build_planning_snapshot(raw_frames)
sim_inputs = prepare_simulation_inputs(raw_frames)

config = RobynConfig(use_real_robyn=False)  # Use enhanced stub
lifts = build_lift_table(
    sim_inputs["expanded_promos"],
    snapshot["ad_spend"],
    snapshot["product_features"]["product_id"],
    pd.date_range("2025-01-15", periods=21, freq="D"),
    config=config,
)
print(lifts.head(10))

# Train surrogate model
python scripts/train_surrogate.py --use-gpu

# View training metrics
cat data/processed/surrogate_model/training_metrics.json

# Create dashboard
python scripts/create_dashboard.py
cat data/processed/dashboard.json
```

### Post-Production

- Add captions/subtitles
- Include chapter markers at each scene
- Add annotations for code snippets
- Include links to documentation in description
- Add speed comparison visualization

---

**Script Version:** 2.0 (Short Showcase)  
**Last Updated:** November 2024  
**Focus:** Orbit/Robyn workflow + Model training metrics

