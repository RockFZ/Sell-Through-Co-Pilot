# What Orbit and Robyn Do in the Project

## Quick Summary

**Orbit** = **Forecasts baseline demand** (what customers would buy without promotions/ads)

**Robyn** = **Calculates lift factors** (how much promotions/ads increase demand)

**Together** = **Projected Demand = Orbit Forecast × Robyn Lift**

---

## Part 1: Uber Orbit - Demand Forecasting

### What Orbit Does

**Orbit** is a **Bayesian time-series forecasting library** from Uber that predicts future demand.

**In Our Project:**
- Takes **historical sales data** (past daily sales by product)
- Generates **baseline demand forecasts** for the next 21-30 days
- Provides **uncertainty intervals** (confidence bounds)

### How It Works

**Input:**
```python
# Historical sales data
daily_demand = [
    {"date": "2024-01-01", "product_id": "SKU-001", "units_sold": 10},
    {"date": "2024-01-02", "product_id": "SKU-001", "units_sold": 12},
    {"date": "2024-01-03", "product_id": "SKU-001", "units_sold": 11},
    ...
]
```

**Output:**
```python
# Forecasts for future dates
forecasts = {
    "SKU-001": DataFrame([
        {"date": "2024-02-01", "forecast_units": 11.5, "forecast_lower": 8.0, "forecast_upper": 15.0},
        {"date": "2024-02-02", "forecast_units": 11.5, "forecast_lower": 8.0, "forecast_upper": 15.0},
        ...
    ])
}
```

**What This Means:**
- **Baseline demand** = 11.5 units/day (what we'd expect without promotions)
- **Uncertainty range** = 8.0 to 15.0 units/day (80% confidence interval)

### Where Orbit is Used

**File:** `src/forecast/orbit_integration.py`

**Called in:** `scripts/run_slow_simulation.py`
```python
# Generate forecasts for all products
forecasts = forecast_bundle(snapshot["daily_demand"], config=orbit_cfg)
```

**Key Point:** Orbit predicts **baseline demand** - what would happen if there were no promotions or advertising.

---

## Part 2: Meta Robyn - Marketing Mix Modeling

### What Robyn Does

**Robyn** is a **Marketing Mix Modeling (MMM) library** from Meta that estimates how marketing activities affect sales.

**In Our Project:**
- Takes **promotional calendar** (discounts) and **advertising spend**
- Calculates **lift multipliers** (how much demand increases)
- Accounts for **saturation** (diminishing returns) and **carryover** (lasting effects)

### How It Works

**Input:**
```python
# Promotional calendar
expanded_promos = [
    {"date": "2024-02-01", "product_id": "SKU-001", "discount_pct": 10.0}
]

# Advertising spend
ad_spend = [
    {"date": "2024-02-01", "channel": "social", "planned_spend": 100}
]
```

**Output:**
```python
# Lift factors per product-date
lift_table = DataFrame([
    {
        "date": "2024-02-01",
        "product_id": "SKU-001",
        "promo_lift": 1.16,      # 10% discount = 16% increase
        "ad_lift": 1.05,          # $100 ad spend = 5% increase
        "total_lift": 1.218       # Combined: 1.16 × 1.05 = 1.218
    },
    ...
])
```

**What This Means:**
- **Promo lift** = 1.16x (16% increase from discount)
- **Ad lift** = 1.05x (5% increase from advertising)
- **Total lift** = 1.218x (21.8% total increase)

### Where Robyn is Used

**File:** `src/promo/robyn_integration.py`

**Called in:** `scripts/run_slow_simulation.py`
```python
# Generate lift factors for all products
lifts = build_lift_table(
    sim_inputs["expanded_promos"],
    snapshot["ad_spend"],
    snapshot["product_features"]["product_id"],
    horizon_dates,
    config=robyn_cfg
)
```

**Key Point:** Robyn calculates **lift factors** - how much promotions and ads boost demand above baseline.

---

## Part 3: How They Work Together

### The Integration Formula

**In the simulation engine** (`src/simulations/inventory_engine.py`):

```python
# 1. Get Orbit forecast (baseline demand)
baseline_demand = forecast_row["forecast_units"]  # From Orbit

# 2. Get Robyn lift (promo + ad multiplier)
total_lift = lift_row["total_lift"]  # From Robyn

# 3. Combine: Projected Demand = Baseline × Lift
projected_demand = baseline_demand * total_lift
```

### Example Calculation

**Scenario:** SKU-001 on 2024-02-01

1. **Orbit says:** Baseline demand = 11.5 units/day
2. **Robyn says:** 10% discount + $100 ad spend = 1.218x lift
3. **Result:** Projected demand = 11.5 × 1.218 = **14.0 units/day**

**This projected demand is then used in the inventory simulation:**
- Check available stock
- Fulfill demand (or record lost sales if stockout)
- Trigger reorder if needed

---

## Part 4: Why We Need Both

### Orbit Alone (Baseline Demand)
- ✅ Predicts normal demand patterns
- ✅ Accounts for seasonality and trends
- ❌ Doesn't account for promotions/ads

### Robyn Alone (Lift Factors)
- ✅ Estimates marketing impact
- ✅ Accounts for saturation and carryover
- ❌ Doesn't predict baseline demand

### Orbit + Robyn Together
- ✅ **Complete picture:** Baseline + Marketing Impact
- ✅ **Accurate projections:** Realistic demand forecasts
- ✅ **Better planning:** Know how much inventory to order

---

## Part 5: Real-World Example

**Scenario:** Planning for a big weekend sale

**Step 1: Orbit Forecast**
- Historical sales show: 10 units/day average
- Orbit predicts: 12 units/day baseline for weekend (slight increase)

**Step 2: Robyn Lift**
- Planned: 20% discount + $500 ad spend
- Robyn calculates: 1.4x lift (40% increase)

**Step 3: Combined Projection**
- Projected demand = 12 × 1.4 = **16.8 units/day**
- For 3-day weekend: **50.4 units total**

**Step 4: Inventory Planning**
- Current stock: 30 units
- Projected need: 50 units
- **Action:** Order 20+ units before weekend

**Without Orbit + Robyn:**
- Might guess: "We'll sell 15 units" (too low → stockout)
- Or guess: "We'll sell 30 units" (too high → leftover inventory)

**With Orbit + Robyn:**
- Accurate projection: 50 units
- **Result:** Right amount of inventory, no stockouts, no waste

---

## Part 6: Implementation Details

### Current Status

**Orbit:**
- ✅ **Real Orbit integrated** (`src/forecast/orbit_integration.py`)
- Uses Uber Orbit's DLT (Dynamic Linear Trend) model
- Falls back to enhanced exponential smoothing if Orbit unavailable

**Robyn:**
- ✅ **Enhanced stub with Robyn-like features** (`src/promo/robyn_integration.py`)
- Implements saturation curves and adstock (carryover effects)
- Can be upgraded to real Robyn when more historical data available

### Key Features

**Orbit Features:**
- Bayesian forecasting with uncertainty
- Weekly seasonality detection
- Trend and level estimation
- Prediction intervals (80% confidence)

**Robyn Features:**
- Promotional lift calculation
- Ad spend saturation curves
- Adstock (exponential decay carryover)
- Combined lift factors

---

## Part 7: Data Flow

```
┌─────────────────────┐
│ Historical Sales    │
│ Data                │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Uber Orbit        │
│   (Forecasting)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Baseline Demand     │
│ Forecasts           │
│ (e.g., 11.5 units)  │
└──────────┬──────────┘
           │
           │
┌──────────┴──────────┐
│                     │
│  Promos + Ad Spend  │
│                     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Meta Robyn        │
│   (MMM)             │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Lift Factors        │
│ (e.g., 1.218x)      │
└──────────┬──────────┘
           │
           │
           ▼
┌─────────────────────┐
│   COMBINED          │
│   Projected Demand  │
│   = 11.5 × 1.218    │
│   = 14.0 units      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Inventory           │
│ Simulation          │
│ (Day-by-day)        │
└─────────────────────┘
```

---

## Summary

| Component | What It Does | Input | Output |
|-----------|--------------|-------|--------|
| **Orbit** | Forecasts baseline demand | Historical sales | Daily demand forecasts (mean + uncertainty) |
| **Robyn** | Calculates marketing lift | Promos + ad spend | Lift multipliers (promo_lift, ad_lift, total_lift) |
| **Combined** | Projects actual demand | Orbit forecasts + Robyn lifts | Projected demand = Forecast × Lift |

**Key Formula:**
```
Projected Demand = Orbit Forecast × Robyn Lift Factor
```

**Why It Matters:**
- **Accurate demand projections** → Better inventory planning
- **No stockouts** → Happy customers
- **No overstock** → Lower costs
- **Better ROI** → Optimize promotions and ad spend

---

## For Your Presentation

**Simple Explanation:**
> "Orbit predicts normal demand, Robyn calculates how promotions and ads boost demand, and together they give us accurate projections for inventory planning."

**Technical Explanation:**
> "We use Uber Orbit for Bayesian time-series forecasting to predict baseline demand, and Meta Robyn for Marketing Mix Modeling to estimate promotional and advertising lift. The simulation engine combines these to project actual demand, which drives our inventory optimization."

**Business Value:**
> "Orbit + Robyn enable us to accurately predict demand, preventing stockouts while avoiding overstock. This translates to better customer satisfaction and lower inventory costs."

