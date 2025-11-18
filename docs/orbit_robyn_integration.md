# How Uber Orbit and Meta Robyn Are Integrated

## Overview

Your project uses **Python facsimiles** (stubs) of Uber Orbit and Meta Robyn that mimic their interfaces and outputs. These stubs generate forecasts and lift factors that feed into the inventory simulation engine. The architecture is designed so you can **swap the stubs for real Orbit/Robyn implementations** without changing the rest of the pipeline.

---

## Integration Architecture

```
┌─────────────────┐
│  Historical     │
│  Sales Data     │ ───┐
└─────────────────┘    │
                       ▼
              ┌──────────────────┐
              │  Uber Orbit      │
              │  (Forecast Stub) │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │  Forecasts       │
              │  (baseline demand)│
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │  Meta Robyn      │
              │  (Lift Stub)      │ ◄─── Promos + Ad Spend
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │  Combined Demand │
              │  = Forecast ×    │
              │    Lift Factor    │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │  Inventory        │
              │  Simulator        │
              └──────────────────┘
```

---

## Part 1: Uber Orbit Integration

### What Orbit Does

**Uber Orbit** is a Bayesian time-series forecasting library that produces:
- **Baseline demand forecasts** (mean predictions)
- **Uncertainty intervals** (confidence bounds)
- **Daily forecasts** for each product

### How It's Integrated in Your Project

**Location:** `src/forecast/orbit_stub.py`

**Current Implementation (Stub):**
```python
def forecast_bundle(daily_demand: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Generates forecasts for each product.
    Returns: {product_id: DataFrame with columns [date, forecast_units, forecast_lower, forecast_upper]}
    """
```

**What the Stub Does:**
1. Takes historical sales data (`daily_demand.parquet`)
2. Applies **exponential smoothing** to estimate baseline demand
3. Calculates uncertainty intervals from historical variance
4. Returns forecasts for the next 30 days per product

**Key Code (lines 59-75):**
```python
def forecast_bundle(daily_demand: pd.DataFrame, config: OrbitStubConfig | None = None) -> Dict[str, pd.DataFrame]:
    config = config or OrbitStubConfig()
    forecasts: Dict[str, pd.DataFrame] = {}
    
    for product_id, group in daily_demand.groupby("product_id"):
        if len(group) < 3:
            continue
        forecasts[product_id] = forecast_product(group, config)  # Generates forecast per product
    
    return forecasts  # Returns {product_id: DataFrame}
```

**Output Format:**
```python
{
    "SKU-001": DataFrame([
        {"date": "2024-01-01", "forecast_units": 12.5, "forecast_lower": 8.2, "forecast_upper": 16.8},
        {"date": "2024-01-02", "forecast_units": 12.5, "forecast_lower": 8.2, "forecast_upper": 16.8},
        ...
    ]),
    "SKU-002": DataFrame([...]),
    ...
}
```

### Where Orbit is Called

**In `scripts/run_slow_simulation.py` (line 30):**
```python
forecasts = forecast_bundle(snapshot["daily_demand"])
```

This generates forecasts for all products before the simulation starts.

### How to Replace with Real Orbit

**Future Implementation:**
```python
from orbit.models import DLT

def forecast_bundle(daily_demand: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    forecasts = {}
    for product_id, group in daily_demand.groupby("product_id"):
        model = DLT(response_col='units_sold', date_col='date')
        model.fit(df=group)
        forecast_df = model.predict(df=group)
        forecasts[product_id] = forecast_df
    return forecasts
```

**No other code changes needed** - the interface stays the same!

---

## Part 2: Meta Robyn Integration

### What Robyn Does

**Meta Robyn** is a Marketing Mix Modeling (MMM) library that estimates:
- **Promotional lift** (how much discount increases demand)
- **Advertising lift** (how ad spend increases demand)
- **Carryover effects** (how past ads/promos affect current demand)

### How It's Integrated in Your Project

**Location:** `src/promo/robyn_stub.py`

**Current Implementation (Stub):**
```python
def build_lift_table(
    expanded_promos: pd.DataFrame,
    ad_spend: pd.DataFrame,
    products: pd.Index,
    horizon_dates: pd.DatetimeIndex
) -> pd.DataFrame:
    """
    Builds a table of lift multipliers per product-date pair.
    Returns: DataFrame with columns [date, product_id, promo_lift, ad_lift, total_lift]
    """
```

**What the Stub Does:**
1. Takes promotional calendar (`expanded_promos`) and ad spend data
2. Calculates **promo lift**: `1.0 + discount_pct × 1.6` (e.g., 10% discount = 1.16x lift)
3. Calculates **ad lift**: `1.0 + ad_spend × 0.0002` with exponential decay
4. Combines them: `total_lift = promo_lift × ad_lift`

**Key Code (lines 56-89):**
```python
def build_lift_table(...) -> pd.DataFrame:
    promo_lift = _promo_lift(expanded_promos, config)  # Promo lift per product-date
    ad_lift = _ad_lift(ad_spend, horizon_dates, config)  # Ad lift per date
    
    # Combine into product-date matrix
    base = pd.MultiIndex.from_product([horizon_dates, products], ...)
    base["promo_lift"] = 1.0
    base["ad_lift"] = 1.0
    
    # Merge promo and ad lifts
    base = base.merge(promo_lift, ...)
    base = base.merge(ad_lift, ...)
    
    base["total_lift"] = base["promo_lift"] * base["ad_lift"]  # Combined multiplier
    return base
```

**Output Format:**
```python
DataFrame([
    {"date": "2024-01-01", "product_id": "SKU-001", "promo_lift": 1.16, "ad_lift": 1.05, "total_lift": 1.218},
    {"date": "2024-01-01", "product_id": "SKU-002", "promo_lift": 1.0, "ad_lift": 1.05, "total_lift": 1.05},
    ...
])
```

### Where Robyn is Called

**In `scripts/run_slow_simulation.py` (lines 37-42):**
```python
lifts = build_lift_table(
    sim_inputs["expanded_promos"],
    snapshot["ad_spend"],
    snapshot["product_features"]["product_id"],
    horizon_dates,
)
```

This generates lift multipliers for all product-date combinations.

### How to Replace with Real Robyn

**Future Implementation:**
```python
from robyn import Robyn

def build_lift_table(...) -> pd.DataFrame:
    # Fit Robyn model on historical sales + spend + promos
    model = Robyn(data=historical_data, ...)
    model.fit()
    
    # Extract response curves
    response_curves = model.get_response_curves()
    
    # Build lift table from curves
    lift_table = apply_response_curves(expanded_promos, ad_spend, response_curves)
    return lift_table
```

**No other code changes needed** - the interface stays the same!

---

## Part 3: How They Work Together in Simulation

### The Integration Point

**In `src/simulations/inventory_engine.py` (lines 85-90):**

```python
for _, row in product_schedule.iterrows():
    date = row["date"]
    
    # 1. Get Orbit forecast (baseline demand)
    forecast_row = product_forecast.loc[date]
    baseline_demand = forecast_row["forecast_units"]  # From Orbit
    
    # 2. Get Robyn lift (promo + ad multiplier)
    lift_row = lift_lookup.loc[(product_id, date)]
    total_lift = lift_row.get("total_lift", 1.0)  # From Robyn
    
    # 3. Combine: Projected Demand = Baseline × Lift
    projected_demand = baseline_demand * total_lift  # ← INTEGRATION POINT
    
    # 4. Use in simulation
    realized_demand = min(available_for_sale, projected_demand)
    lost_sales = max(projected_demand - available_for_sale, 0.0)
```

### The Formula

```
Projected Demand = Orbit Forecast × Robyn Lift Factor

Example:
- Orbit says: "Baseline demand = 10 units/day"
- Robyn says: "10% discount + $100 ad spend = 1.2x lift"
- Result: Projected demand = 10 × 1.2 = 12 units/day
```

### Data Flow Example

**Day 1 of Simulation:**

1. **Orbit Input:** Historical sales for SKU-001
   ```python
   daily_demand = [
       {"date": "2024-01-01", "product_id": "SKU-001", "units_sold": 10},
       {"date": "2024-01-02", "product_id": "SKU-001", "units_sold": 12},
       ...
   ]
   ```

2. **Orbit Output:** Forecast for SKU-001 on 2024-02-01
   ```python
   {"date": "2024-02-01", "forecast_units": 11.5, "forecast_lower": 8.0, "forecast_upper": 15.0}
   ```

3. **Robyn Input:** Promo calendar + ad spend
   ```python
   expanded_promos = [
       {"date": "2024-02-01", "product_id": "SKU-001", "discount_pct": 10.0}
   ]
   ad_spend = [
       {"date": "2024-02-01", "channel": "social", "planned_spend": 100}
   ]
   ```

4. **Robyn Output:** Lift factor
   ```python
   {"date": "2024-02-01", "product_id": "SKU-001", "total_lift": 1.218}
   ```

5. **Simulation Calculation:**
   ```python
   projected_demand = 11.5 × 1.218 = 14.0 units
   ```

6. **Inventory Simulation:**
   - Check available stock
   - Fulfill demand (or record lost sales)
   - Trigger reorder if needed

---

## Part 4: Why Use Stubs?

### Current Approach (Stubs)

**Advantages:**
- ✅ **Fast development** - No need to install/configure Orbit/Robyn yet
- ✅ **Reproducible** - Simple algorithms, easy to debug
- ✅ **Same interface** - Drop-in replacement when ready
- ✅ **Proof of concept** - Validates the integration architecture

**Limitations:**
- ⚠️ Less accurate than real Orbit/Robyn
- ⚠️ Missing advanced features (seasonality, saturation curves, etc.)

### Future Approach (Real Orbit/Robyn)

**When to Switch:**
- Milestone 2-3: Replace stubs with real implementations
- Need higher accuracy for production
- Want to leverage Orbit's Bayesian uncertainty
- Want Robyn's sophisticated MMM capabilities

**Migration Path:**
1. Install Orbit: `pip install orbit-ml`
2. Install Robyn: `pip install robyn`
3. Replace stub functions with real API calls
4. **No changes needed** to simulation engine or pipeline!

---

## Part 5: Key Integration Points Summary

| Component | File | Function | Input | Output |
|-----------|------|----------|-------|--------|
| **Orbit Stub** | `src/forecast/orbit_stub.py` | `forecast_bundle()` | Historical sales | `{product_id: forecast_df}` |
| **Robyn Stub** | `src/promo/robyn_stub.py` | `build_lift_table()` | Promos + ads | `DataFrame[date, product_id, total_lift]` |
| **Simulation** | `src/simulations/inventory_engine.py` | `run_inventory_simulation()` | Forecasts + lifts | Simulation logs |
| **Orchestration** | `scripts/run_slow_simulation.py` | `run_pipeline()` | Raw data | Complete simulation |

---

## Part 6: Testing the Integration

**Run the full pipeline:**
```bash
python scripts/run_slow_simulation.py --horizon-days 21
```

**What happens:**
1. Loads historical sales → Orbit generates forecasts
2. Loads promos + ads → Robyn generates lifts
3. Simulation combines them → Generates training data
4. Outputs: `data/processed/slow_simulations/sim_log.parquet`

**Check the integration:**
```python
import pandas as pd

# Load simulation log
log = pd.read_parquet("data/processed/slow_simulations/sim_log.parquet")

# See how Orbit + Robyn combined
print(log[["product_id", "date", "projected_demand"]].head(10))
# projected_demand = Orbit forecast × Robyn lift
```

---

## Summary

**Orbit** provides **baseline demand forecasts** (what demand would be without promotions/ads).

**Robyn** provides **lift multipliers** (how much promotions/ads increase demand).

**The simulation** combines them: `Projected Demand = Orbit Forecast × Robyn Lift`

**The architecture** is designed so you can swap stubs for real Orbit/Robyn implementations without changing any other code.

This is the foundation for generating training data for your AI surrogate model!


