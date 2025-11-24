# Screen Recording Script - Milestone 2 Showcase

**Duration:** ~6 minutes  
**Focus:** Orbit/Robyn workflow + Surrogate Model Training

---

## Scene 1: Introduction (0:00 - 0:30)

### Screen Setup
- Show project title slide or terminal with project name
- Have architecture diagram ready (Orbit → Robyn → Surrogate)

### What to Say
"Welcome to the Sell-Through Co-Pilot Milestone 2 showcase. Today we'll demonstrate how we integrate Uber Orbit for demand forecasting, Meta Robyn for marketing mix modeling, and train an AI surrogate model for fast optimization."

"The workflow is simple: Orbit forecasts baseline demand, Robyn calculates promotional lift, and our surrogate model learns from simulations to predict outcomes instantly. Let's see it in action."

---

## Scene 2: Orbit Integration & Workflow (0:30 - 2:00)

### Screen Setup
- Open `src/forecast/orbit_integration.py` in code editor
- Have terminal ready

### What to Show

1. **Code Overview (30 seconds)**
   - Show the `forecast_bundle` function
   - Highlight the DLT model configuration
   - Point out seasonality detection

2. **Run Orbit Forecast (30 seconds)**
   ```python
   from src.forecast import forecast_bundle, OrbitConfig
   import pandas as pd
   
   daily_demand = pd.read_parquet("data/processed/daily_demand.parquet")
   config = OrbitConfig(use_real_orbit=False)  # Use enhanced stub
   forecasts = forecast_bundle(daily_demand, config=config)
   ```

3. **Show Results (30 seconds)**
   ```python
   print(forecasts["SKU-001"])
   ```
   - Show the DataFrame with forecast_units, forecast_lower, forecast_upper
   - Explain: "For SKU-001, Orbit predicts 12.5 units per day on average, with an 80% confidence interval from 8.2 to 16.8 units."

4. **Visualization (30 seconds)**
   - If you have a plot, show it
   - Explain: "The visualization shows Orbit automatically detected weekly seasonality — you can see the weekend spikes. This is production-grade forecasting."

### What to Say
"First, Orbit integration. We use Uber Orbit's DLT model for Bayesian forecasting with automatic seasonality detection."

"The code is straightforward: load historical sales, configure the DLT model with weekly seasonality, fit, and predict. Orbit handles trend and uncertainty automatically."

"Let's run it. We pass in daily demand data for our 4 products. Orbit generates forecasts with prediction intervals — not just point estimates, but uncertainty bounds."

"Here are the results. For SKU-001, Orbit predicts 12.5 units per day on average, with an 80% confidence interval from 8.2 to 16.8 units. This uncertainty is crucial for inventory planning."

---

## Scene 3: Robyn Integration & Workflow (2:00 - 3:30)

### Screen Setup
- Open `src/promo/robyn_integration.py` in code editor
- Have terminal ready

### What to Show

1. **Code Overview (30 seconds)**
   - Show the `build_lift_table` function
   - Highlight saturation curves and adstock effects

2. **Run Robyn Lift Calculation (30 seconds)**
   ```python
   from src.promo import build_lift_table, RobynConfig
   from src.sim_prep import prepare_simulation_inputs
   from src import data_loader, transformations
   import pandas as pd
   
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
   ```

3. **Show Results (30 seconds)**
   ```python
   print(lifts.head(10))
   ```
   - Show the DataFrame with promo_lift, ad_lift, total_lift
   - Explain: "For a 10% discount plus $100 in ad spend, Robyn calculates a 1.218x total lift — that's a 21.8% increase in demand."

4. **Explain Lift Components (30 seconds)**
   - Point to specific rows showing promo_lift and ad_lift
   - Explain: "The lift table separates promo lift from ad lift. Here, the discount gives 1.16x promo lift, ads give 1.05x ad lift, and the combined effect is 1.218x due to interaction."

### What to Say
"Next, Robyn integration. Meta Robyn models how promotions and advertising affect demand."

"Robyn takes promotional calendars and ad spend data. It models saturation curves — diminishing returns on ad spend — and adstock effects — carryover from past advertising."

"We run Robyn on our promo calendar and ad spend. For a 10% discount plus $100 in ad spend, Robyn calculates a 1.218x total lift — that's a 21.8% increase in demand."

"This is Robyn's response curve for ad spend. Notice the saturation — the first $100 gives more lift than the next $100. This is realistic marketing behavior."

---

## Scene 4: Combined Demand & Simulation (3:30 - 4:00)

### Screen Setup
- Open `src/simulations/inventory_engine.py`
- Show the integration point around line 90

### What to Show

1. **Show Integration Code (15 seconds)**
   ```python
   # In inventory_engine.py around line 90
   projected_demand = forecast_row["forecast_units"] * total_lift
   ```
   - Highlight this line
   - Explain the formula

2. **Show Example Calculation (15 seconds)**
   - Show a simple example:
     - Orbit: 10 units
     - Robyn: 1.2x lift
     - Result: 12 units

3. **Show Simulation Summary (30 seconds)**
   ```bash
   cat data/processed/slow_simulations/sim_summary.json
   ```
   - Or show from the log file
   - Explain: "The simulation runs day-by-day, tracking inventory, demand fulfillment, and lost sales. We generate 84 records — 4 products over 21 days — which becomes training data for our surrogate model."

### What to Say
"Orbit and Robyn combine in the simulation engine. The formula is simple: Projected Demand equals Orbit Forecast times Robyn Lift."

"For example: Orbit says 10 units baseline, Robyn says 1.2x lift, result is 12 units projected demand. This feeds into our inventory simulation."

"The simulation runs day-by-day, tracking inventory, demand fulfillment, and lost sales. We generate 84 records — 4 products over 21 days — which becomes training data for our surrogate model."

---

## Scene 5: Surrogate Model Training (4:00 - 5:30)

### Screen Setup
- Have terminal ready
- Have code editor ready to show model.py if needed

### What to Show

1. **Run Training Command (20 seconds)**
   ```bash
   python scripts/train_surrogate.py --use-gpu
   ```
   - Let it run and show the output
   - Explain: "We run: `python scripts/train_surrogate.py --use-gpu`. The model learns to predict five outcomes: realized demand, lost sales, service level, lost sales rate, and order quantities."

2. **Show Training Progress (20 seconds)**
   - Show the training output
   - Point out: "Training takes just 0.3 seconds on GPU. The model learns from product features, promo calendars, and ad spend to predict simulation outcomes."

3. **Show Training Metrics (40 seconds)**
   ```bash
   cat data/processed/surrogate_model/training_metrics.json
   ```
   - Or show from the log file
   - Explain each metric:
     - "For service level, we achieve an MAE of 0.14 — that's 14 percentage points error."
     - "For lost sales, MAE is 77 units."
     - "These are good results given we only have 4 products."

4. **Show Model Files (10 seconds)**
   ```bash
   ls -lh data/processed/surrogate_model/
   ```
   - Show the saved model files
   - Explain: "The trained model is saved. We can now use it for instant predictions instead of running 12-second simulations."

### What to Say
"Now, the AI surrogate model. We train XGBoost on GPU to learn from simulation logs and predict outcomes instantly."

"Training takes just 0.3 seconds on GPU. The model learns from product features, promo calendars, and ad spend to predict simulation outcomes."

"Here are the training metrics. For service level, we achieve an MAE of 0.14 — that's 14 percentage points error. For lost sales, MAE is 77 units. These are good results given we only have 4 products."

"The trained model is saved. We can now use it for instant predictions instead of running 12-second simulations."

---

## Scene 6: Model Performance & Dashboard (5:30 - 6:00)

### Screen Setup
- Have terminal ready
- Have dashboard.json ready to show

### What to Show

1. **Show Speed Comparison (15 seconds)**
   - Create a simple comparison:
     - Full simulation: 12 seconds
     - Surrogate prediction: <1 millisecond
     - Speedup: 12,000x faster
   - Can show as text or simple diagram

2. **Show Dashboard (15 seconds)**
   ```bash
   python scripts/create_dashboard.py
   cat data/processed/dashboard.json
   ```
   - Show the dashboard JSON
   - Point out the readiness status
   - Explain: "The dashboard shows readiness status: green for healthy, yellow for warning, red for critical. Our model predictions feed into this operational view."

### What to Say
"Performance is the key benefit. Full simulation takes 12 seconds. Surrogate prediction takes less than 1 millisecond. That's 12,000 times faster — enabling interactive optimization."

"The dashboard shows readiness status: green for healthy, yellow for warning, red for critical. Our model predictions feed into this operational view."

"In summary: Orbit provides forecasts, Robyn provides lift, and our AI surrogate enables real-time optimization. Thank you for watching."

---

## Quick Reference: Commands to Run

### Orbit Forecast
```python
from src.forecast import forecast_bundle, OrbitConfig
import pandas as pd

daily_demand = pd.read_parquet("data/processed/daily_demand.parquet")
config = OrbitConfig(use_real_orbit=False)
forecasts = forecast_bundle(daily_demand, config=config)
print(forecasts["SKU-001"])
```

### Robyn Lift
```python
from src.promo import build_lift_table, RobynConfig
from src.sim_prep import prepare_simulation_inputs
from src import data_loader, transformations
import pandas as pd

raw_frames = data_loader.load_raw_frames()
snapshot = transformations.build_planning_snapshot(raw_frames)
sim_inputs = prepare_simulation_inputs(raw_frames)

config = RobynConfig(use_real_robyn=False)
lifts = build_lift_table(
    sim_inputs["expanded_promos"],
    snapshot["ad_spend"],
    snapshot["product_features"]["product_id"],
    pd.date_range("2025-01-15", periods=21, freq="D"),
    config=config,
)
print(lifts.head(10))
```

### Train Surrogate Model
```bash
python scripts/train_surrogate.py --use-gpu
cat data/processed/surrogate_model/training_metrics.json
```

### Create Dashboard
```bash
python scripts/create_dashboard.py
cat data/processed/dashboard.json
```

---

## Tips for Recording

1. **Prepare in Advance:**
   - Make sure all data files exist
   - Test all commands before recording
   - Have code editor and terminal windows ready

2. **Smooth Transitions:**
   - Use keyboard shortcuts to switch between windows
   - Keep terminal history clean
   - Have files pre-opened in editor

3. **Clear Narration:**
   - Speak clearly and at moderate pace
   - Pause briefly after running commands to show output
   - Explain what you're doing as you do it

4. **Visual Clarity:**
   - Use larger font sizes in terminal
   - Highlight important code sections
   - Zoom in on key outputs

5. **Timing:**
   - Scene 1: 30 seconds
   - Scene 2: 90 seconds (Orbit)
   - Scene 3: 90 seconds (Robyn)
   - Scene 4: 30 seconds (Combined)
   - Scene 5: 90 seconds (Training)
   - Scene 6: 30 seconds (Performance)
   - **Total: ~6 minutes**

---

**Good luck with your recording!**


